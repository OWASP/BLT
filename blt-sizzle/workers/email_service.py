# pyright: reportMissingImports=false, reportOptionalMemberAccess=false, reportOptionalCall=false
"""Transactional email for BLT Sizzle (login codes and daily reminders).

EMAIL_PROVIDER picks the API: sendgrid (default), resend, mailgun or mailtrap. All of them
read EMAIL_API_KEY and EMAIL_FROM ("noreply@example.org" or "Name <noreply@example.org>").
Mailgun also needs its sending domain: EMAIL_DOMAIN, else the EMAIL_FROM domain; set
EMAIL_API_BASE=https://api.eu.mailgun.net for an EU Mailgun account.

Results never carry the API key. Provider error text is shortened and has email
addresses masked before it is returned or logged.
"""
import base64
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request


SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
RESEND_API_URL = "https://api.resend.com/emails"
MAILTRAP_API_URL = "https://send.api.mailtrap.io/api/send"
MAILGUN_API_BASE = "https://api.mailgun.net"
SUPPORTED_PROVIDERS = ("sendgrid", "resend", "mailgun", "mailtrap")

try:  # pragma: no cover - only available in the Cloudflare Workers runtime.
    from js import Headers as JsHeaders
    from js import Object as JsObject
    from js import fetch as js_fetch
    from pyodide.ffi import to_js as js_to_js
except ImportError:  # pragma: no cover - local tests use the urllib fallback.
    JsHeaders = None
    JsObject = None
    js_fetch = None
    js_to_js = None


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_FROM_RE = re.compile(r"^\s*(?:\"?([^\"<]*?)\"?\s*)?<\s*([^<>\s]+@[^<>\s]+)\s*>\s*$")


def mask_emails(text):
    """Replace every address with ***@domain."""
    return _EMAIL_RE.sub(lambda m: "***@" + m.group(1), str(text or ""))


def parse_from_address(value, default_name=""):
    """'Name <a@b.org>' or 'a@b.org' -> (email, name)."""
    value = str(value or "").strip()
    match = _FROM_RE.match(value)
    if match:
        return match.group(2).strip(), (match.group(1) or "").strip() or default_name
    return value, default_name


def _format_from(email, name):
    if name:
        safe = name.replace('"', "").replace("<", "").replace(">", "")
        return f'"{safe}" <{email}>' if any(c in safe for c in ',;') else f"{safe} <{email}>"
    return email


async def http_post(url, headers, body, timeout=30):
    """POST and return (status, response_text). Status 0 means the request never completed."""
    try:
        if js_fetch is not None and JsHeaders is not None and JsObject is not None:  # pragma: no cover
            js_headers = JsHeaders.new(js_to_js([[k, v] for k, v in headers.items()]))
            init = JsObject.new()
            init.method = "POST"
            init.headers = js_headers
            init.body = body
            response = await js_fetch(url, init)
            return int(response.status), str(await response.text())
        data = body.encode("utf-8") if isinstance(body, str) else body
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return int(response.status), response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            return int(error.code), error.read().decode("utf-8", "replace")
    except Exception:
        return 0, ""


def build_sendgrid_payload(
    to_email,
    subject,
    html_content,
    from_email,
    from_name,
    custom_args=None,
    text_content=None,
):
    content = []
    if text_content:
        # SendGrid requires text/plain before text/html.
        content.append({"type": "text/plain", "value": text_content})
    content.append({"type": "text/html", "value": html_content})
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": content,
    }

    if custom_args:
        payload["custom_args"] = dict(custom_args)

    return payload


def build_provider_request(provider, api_key, from_email, from_name, to_email, subject,
                           html_content, text_content=None, custom_args=None,
                           domain="", api_base=""):
    """Return (url, headers, body) for one message. Pure, so it is unit-tested per provider."""
    provider = (provider or "sendgrid").lower()
    if provider == "sendgrid":
        payload = build_sendgrid_payload(to_email, subject, html_content, from_email, from_name,
                                         custom_args=custom_args, text_content=text_content)
        return SENDGRID_API_URL, {"Authorization": "Bearer " + api_key,
                                  "Content-Type": "application/json"}, json.dumps(payload, separators=(",", ":"))
    if provider == "resend":
        payload = {"from": _format_from(from_email, from_name), "to": [to_email],
                   "subject": subject, "html": html_content}
        if text_content:
            payload["text"] = text_content
        if custom_args:
            payload["tags"] = [{"name": re.sub(r"[^A-Za-z0-9_-]", "_", str(k)),
                                "value": re.sub(r"[^A-Za-z0-9_-]", "_", str(v))}
                               for k, v in custom_args.items()]
        return RESEND_API_URL, {"Authorization": "Bearer " + api_key,
                                "Content-Type": "application/json"}, json.dumps(payload, separators=(",", ":"))
    if provider == "mailtrap":
        payload = {"from": {"email": from_email, "name": from_name}, "to": [{"email": to_email}],
                   "subject": subject, "html": html_content}
        if text_content:
            payload["text"] = text_content
        if custom_args:
            payload["custom_variables"] = {str(k): str(v) for k, v in custom_args.items()}
            if custom_args.get("purpose"):
                payload["category"] = str(custom_args["purpose"])
        return MAILTRAP_API_URL, {"Authorization": "Bearer " + api_key,
                                  "Content-Type": "application/json"}, json.dumps(payload, separators=(",", ":"))
    if provider == "mailgun":
        domain = domain or (from_email.rsplit("@", 1)[1] if "@" in from_email else "")
        base = (api_base or MAILGUN_API_BASE).rstrip("/")
        form = [("from", _format_from(from_email, from_name)), ("to", to_email),
                ("subject", subject), ("html", html_content)]
        if text_content:
            form.append(("text", text_content))
        for key, value in (custom_args or {}).items():
            form.append((f"v:{key}", str(value)))
        auth = base64.b64encode(("api:" + api_key).encode("utf-8")).decode("ascii")
        return (f"{base}/v3/{urllib.parse.quote(domain)}/messages",
                {"Authorization": "Basic " + auth, "Content-Type": "application/x-www-form-urlencoded"},
                urllib.parse.urlencode(form))
    raise ValueError("Unsupported email provider")


class EmailService:
    """Send one message through EMAIL_PROVIDER, retrying a transient failure at most once."""

    def __init__(self, provider, api_key, from_email, from_name="BLT Sizzle", domain="",
                 api_base="", transport=None, max_attempts=2):
        self.provider = (provider or "sendgrid").strip().lower()
        self.api_key = api_key or ""
        parsed_email, parsed_name = parse_from_address(from_email, from_name or "BLT Sizzle")
        self.from_email = parsed_email
        self.from_name = parsed_name or "BLT Sizzle"
        self.domain = domain or ""
        self.api_base = api_base or ""
        self._post = transport or http_post
        self.max_attempts = max(1, min(int(max_attempts), 2))

    @classmethod
    def from_env(cls, env, transport=None):
        def value(*names, default=""):
            for name in names:
                found = getattr(env, name, "") or ""
                if found:
                    return str(found)
            return default
        return cls(
            value("EMAIL_PROVIDER", default="sendgrid"),
            value("EMAIL_API_KEY", "SENDGRID_API_KEY"),
            value("EMAIL_FROM", "SENDGRID_FROM_EMAIL"),
            value("EMAIL_FROM_NAME", "SENDGRID_FROM_NAME", default="BLT Sizzle"),
            domain=value("EMAIL_DOMAIN", "MAILGUN_DOMAIN"),
            api_base=value("EMAIL_API_BASE", "MAILGUN_API_BASE"),
            transport=transport,
        )

    def is_supported(self):
        return self.provider in SUPPORTED_PROVIDERS

    def is_configured(self):
        return bool(self.is_supported() and self.api_key and "@" in self.from_email)

    def describe(self):
        """Config summary that is safe to log: never the key or the full sender."""
        return {
            "provider": self.provider,
            "supported": self.is_supported(),
            "api_key_present": bool(self.api_key),
            "from_domain": self.from_email.rsplit("@", 1)[1] if "@" in self.from_email else "",
        }

    async def send_email(self, to_email, subject, html_content, custom_args=None, text_content=None):
        if not self.is_supported():
            return _result(self.provider, 503, "Email provider is not supported.", attempts=0, retryable=False)
        if not self.is_configured():
            return _result(self.provider, 503, "Email service is not configured.", attempts=0, retryable=False)
        url, headers, body = build_provider_request(
            self.provider, self.api_key, self.from_email, self.from_name, to_email, subject,
            html_content, text_content=text_content, custom_args=custom_args,
            domain=self.domain, api_base=self.api_base,
        )
        result = None
        for attempt in range(1, self.max_attempts + 1):
            status, response_text = await self._post(url, headers, body)
            result = _result(self.provider, status, response_text, attempts=attempt)
            if result["success"] or not result["retryable"]:
                break
        return result


class SendGridEmailService(EmailService):
    def __init__(self, api_key, from_email, from_name="BLT Sizzle", api_url=SENDGRID_API_URL, transport=None):
        super().__init__("sendgrid", api_key, from_email, from_name, transport=transport)
        self.api_url = api_url


def _provider_message_id(provider, response_text):
    if provider in ("resend", "mailgun", "mailtrap"):
        try:
            data = json.loads(response_text or "{}")
        except ValueError:
            return ""
        if isinstance(data, dict):
            ids = data.get("message_ids")
            if isinstance(ids, list) and ids:
                return str(ids[0])
            return str(data.get("id") or "")
    return ""


def _result(provider, status, response_text, attempts=1, retryable=None):
    status = int(status or 0)
    success = 200 <= status < 300
    if retryable is None:
        retryable = status in {0, 408, 429} or status >= 500
    detail = ""
    if not success:
        detail = mask_emails(re.sub(r"\s+", " ", str(response_text or "")))[:300]
    if success:
        error = ""
    elif status == 0:
        error = f"{provider} request failed."
    elif status == 503 and attempts == 0:
        error = response_text
        detail = ""
    else:
        error = f"{provider} returned status {status}."
    return {
        "success": success,
        "status": status,
        "provider": provider,
        "attempts": attempts,
        "retryable": (not success) and bool(retryable),
        "permanent_failure": (not success) and not bool(retryable),
        "provider_message_id": _provider_message_id(provider, response_text) if success else "",
        "error": error,
        "detail": detail,
    }


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


