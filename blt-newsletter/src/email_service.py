import json
import urllib.error
import urllib.request


SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"

try:  # pragma: no cover - only available in the Cloudflare Workers runtime.
    from js import Headers as JsHeaders
    from js import Object as JsObject
    from js import fetch as js_fetch
except ImportError:  # pragma: no cover - local tests use the urllib fallback.
    JsHeaders = None
    JsObject = None
    js_fetch = None


def build_sendgrid_payload(
    to_email,
    subject,
    html_content,
    from_email,
    from_name,
    custom_args=None,
):
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_content}],
    }

    if custom_args:
        payload["custom_args"] = dict(custom_args)

    return payload


class SendGridEmailService:
    def __init__(
        self,
        api_key,
        from_email,
        from_name="OWASP BLT",
        api_url=SENDGRID_API_URL,
    ):
        self.api_key = api_key or ""
        self.from_email = from_email or ""
        self.from_name = from_name or "OWASP BLT"
        self.api_url = api_url

    def is_configured(self):
        return bool(self.api_key and self.from_email)

    async def send_email(self, to_email, subject, html_content, custom_args=None):
        if not self.is_configured():
            return _sendgrid_result(503, "SendGrid is not configured.")

        payload = build_sendgrid_payload(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            from_email=self.from_email,
            from_name=self.from_name,
            custom_args=custom_args,
        )
        body = json.dumps(payload, separators=(",", ":"))

        try:
            if js_fetch is not None and JsHeaders is not None and JsObject is not None:
                status, response_text, message_id = await self._send_with_workers_fetch(body)
            else:
                status, response_text, message_id = self._send_with_urllib(body)
        except (urllib.error.URLError, TimeoutError, OSError, ConnectionError):
            return _sendgrid_result(0, "SendGrid request failed.", retryable=True)

        return _sendgrid_result(status, response_text, message_id=message_id)

    async def _send_with_workers_fetch(self, body):
        headers = JsHeaders.new(
            [
                ["Authorization", "Bearer " + self.api_key],
                ["Content-Type", "application/json"],
            ]
        )
        request_init = JsObject.new()
        request_init.method = "POST"
        request_init.headers = headers
        request_init.body = body

        response = await js_fetch(self.api_url, request_init)
        response_text = await response.text()
        message_id = ""
        try:
            message_id = response.headers.get("x-message-id") or ""
        except Exception:
            message_id = ""

        return int(response.status), response_text, message_id

    def _send_with_urllib(self, body):
        request = urllib.request.Request(
            self.api_url,
            data=body.encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_text = response.read().decode("utf-8")
                message_id = response.headers.get("x-message-id", "")
                return int(response.status), response_text, message_id
        except urllib.error.HTTPError as error:
            response_text = error.read().decode("utf-8")
            message_id = error.headers.get("x-message-id", "")
            return int(error.code), response_text, message_id


def _sendgrid_result(status, response_text, message_id="", retryable=None):
    success = 200 <= int(status or 0) < 300
    if retryable is None:
        retryable = int(status or 0) in {0, 408, 429} or int(status or 0) >= 500

    return {
        "success": success,
        "status": int(status or 0),
        "provider": "sendgrid",
        "retryable": (not success) and bool(retryable),
        "permanent_failure": (not success) and not bool(retryable),
        "provider_message_id": message_id or "",
        "error": "" if success else _safe_error_message(status, response_text),
    }


def _safe_error_message(status, response_text):
    if int(status or 0) == 0:
        return "SendGrid request failed."

    return "SendGrid returned status " + str(int(status or 0)) + "."
