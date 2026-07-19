# pyright: reportMissingImports=false, reportOptionalMemberAccess=false, reportOptionalCall=false
import html
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
        from_name="BLT Sizzle",
        api_url=SENDGRID_API_URL,
    ):
        self.api_key = api_key or ""
        self.from_email = from_email or ""
        self.from_name = from_name or "BLT Sizzle"
        self.api_url = api_url

    def is_configured(self):
        return bool(self.api_key and self.from_email)

    async def send_email(self, to_email, subject, html_content, custom_args=None):
        if not self.is_configured():
            return _sendgrid_result(503, "SendGrid is not configured.", retryable=False)

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


def render_otp_email(email, otp, app_name="BLT Sizzle"):
    safe_email = html.escape(str(email or ""))
    safe_otp = html.escape(str(otp or ""))
    safe_app = html.escape(str(app_name or "BLT Sizzle"))
    return f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_app} verification code</title>
  </head>
  <body style="margin:0;background:#f8fafc;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#0f172a;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;overflow:hidden;">
            <tr>
              <td style="padding:28px 28px 8px;">
                <p style="margin:0 0 10px;color:#dc2626;font-size:12px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;">{safe_app}</p>
                <h1 style="margin:0;font-size:28px;line-height:1.2;color:#111827;">Your verification code</h1>
                <p style="margin:16px 0 0;color:#475569;font-size:15px;line-height:1.6;">Use this one-time code to continue signing in as <strong>{safe_email}</strong>.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 28px;">
                <div style="background:#111827;color:#ffffff;border-radius:14px;text-align:center;font-size:36px;letter-spacing:.35em;font-weight:800;padding:22px 18px;">{safe_otp}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 28px;color:#64748b;font-size:13px;line-height:1.6;">
                This code expires soon. If you did not request it, you can safely ignore this email.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()


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
    if int(status or 0) == 503:
        return "SendGrid is not configured."
    return "SendGrid returned status " + str(int(status or 0)) + "."
