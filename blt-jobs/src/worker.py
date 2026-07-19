import base64
import hashlib
import hmac
import html
import json
import re
import time
from urllib.parse import urlparse

try:
    from js import Object, fetch as js_fetch
    from pyodide.ffi import to_js as _to_js
    from workers import WorkerEntrypoint, Response
except ModuleNotFoundError:
    class WorkerEntrypoint:
        pass

    class Response:
        def __init__(self, body="", status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = headers or {}

    async def fetch_url(*_args, **_kwargs):
        raise RuntimeError("Cloudflare fetch is only available in the Worker runtime")
else:
    def to_js(value):
        return _to_js(value, dict_converter=Object.fromEntries)

    async def fetch_url(url, options):
        return await js_fetch(url, to_js(options))


DEFAULT_ADMIN_PATH = "/admin"
DEFAULT_FROM = "jobs@owaspblt.org"
SESSION_COOKIE = "blt_jobs_admin"
SESSION_TTL_SECONDS = 60 * 60 * 8
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(str(request.url))
        admin_path = normalize_admin_path(env_value(self.env, "ADMIN_PATH", DEFAULT_ADMIN_PATH))

        if url.path == "/admin.html" and admin_path != "/admin.html":
            return not_found()

        if url.path in (admin_path, f"{admin_path}/"):
            return await self.env.ASSETS.fetch("https://assets.local/admin.html")

        if url.path.startswith("/api/admin/"):
            return await handle_admin_api(request, self.env, url.path)

        return await self.env.ASSETS.fetch(request)


async def handle_admin_api(request, env, path):
    if request.method == "OPTIONS":
        return Response("", status=204)

    if path == "/api/admin/session" and request.method == "GET":
        return json_response({"authenticated": is_authenticated(request, env)})

    if path == "/api/admin/login" and request.method == "POST":
        body = await read_json(request)
        username = str(field(body, "username", ""))
        password = str(field(body, "password", ""))

        admin_user = env_value(env, "ADMIN_USER", "")
        admin_pass = env_value(env, "ADMIN_PASS", "")
        if not admin_user or not admin_pass:
            return json_response({"error": "Admin credentials are not configured."}, status=500)

        if not timing_safe_equal(username, admin_user) or not timing_safe_equal(password, admin_pass):
            return json_response({"error": "Invalid username or password."}, status=401)

        token = create_session_token(env)
        secure = "; Secure" if urlparse(str(request.url)).scheme == "https" else ""
        return json_response(
            {"authenticated": True},
            headers={
                "Set-Cookie": (
                    f"{SESSION_COOKIE}={token}; Path=/; Max-Age={SESSION_TTL_SECONDS}; "
                    f"HttpOnly; SameSite=Strict{secure}"
                )
            },
        )

    if path == "/api/admin/logout" and request.method == "POST":
        return json_response(
            {"authenticated": False},
            headers={"Set-Cookie": f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"},
        )

    if path == "/api/admin/send" and request.method == "POST":
        if not is_authenticated(request, env):
            return json_response({"error": "Authentication required."}, status=401)

        body = await read_json(request)
        recipients = normalize_recipients(field(body, "recipients", []))
        subject = str(field(body, "subject", "")).strip()
        message = str(field(body, "message", "")).strip()

        if not recipients:
            return json_response({"error": "Add at least one valid recipient email."}, status=400)
        if not subject:
            return json_response({"error": "Subject is required."}, status=400)
        if not message:
            return json_response({"error": "Message is required."}, status=400)

        try:
            provider = await send_candidate_email(env, recipients, subject, message)
            return json_response({"ok": True, "sent": len(recipients), "provider": provider})
        except Exception as error:
            return json_response({"error": str(error) or "Unable to send email."}, status=502)

    return not_found()


async def send_candidate_email(env, recipients, subject, message):
    from_email = env_value(env, "EMAIL_FROM", DEFAULT_FROM)
    sendgrid_key = env_value(env, "SENDGRID_API_KEY", "")
    if not sendgrid_key:
        raise ValueError("SendGrid is not configured.")

    response = await fetch_url(
        "https://api.sendgrid.com/v3/mail/send",
        {
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {sendgrid_key}",
                "Content-Type": "application/json",
            },
            "body": json.dumps(
                {
                    "personalizations": [{"to": [{"email": email} for email in recipients]}],
                    "from": {"email": from_email},
                    "subject": subject,
                    "content": [
                        {"type": "text/plain", "value": message},
                        {"type": "text/html", "value": text_to_html(message)},
                    ],
                }
            ),
        },
    )

    if not response.ok:
        raise ValueError(await provider_error(response))

    return "sendgrid"


def create_session_token(env):
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = base64_url_encode(json.dumps({"exp": expires_at}, separators=(",", ":")).encode())
    signature = sign(payload, session_secret(env))
    return f"{payload}.{signature}"


def is_authenticated(request, env):
    token = get_cookie(request.headers.get("Cookie") or "", SESSION_COOKIE)
    if not token or "." not in token:
        return False

    payload, signature = token.split(".", 1)
    expected = sign(payload, session_secret(env))
    if not timing_safe_equal(signature, expected):
        return False

    try:
        parsed = json.loads(base64_url_decode(payload).decode())
        return int(parsed.get("exp", 0)) > int(time.time())
    except Exception:
        return False


def session_secret(env):
    return env_value(env, "ADMIN_SESSION_SECRET", "") or env_value(env, "ADMIN_PASS", "") or "unset-admin-secret"


def sign(value, secret):
    digest = hmac.new(str(secret).encode(), str(value).encode(), hashlib.sha256).digest()
    return base64_url_encode(digest)


def timing_safe_equal(left, right):
    return hmac.compare_digest(str(left).encode(), str(right).encode())


def normalize_recipients(value):
    if isinstance(value, str):
        raw = value
    else:
        try:
            raw = ",".join(str(item) for item in value)
        except TypeError:
            raw = str(value or "")

    recipients = []
    seen = set()
    for email in re.split(r"[,\s;]+", raw):
        normalized = email.strip().lower()
        if EMAIL_PATTERN.match(normalized) and normalized not in seen:
            seen.add(normalized)
            recipients.append(normalized)
    return recipients


async def read_json(request):
    try:
        return await request.json()
    except Exception:
        return {}


def field(value, name, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    try:
        return value[name]
    except Exception:
        return getattr(value, name, default)


def env_value(env, name, default=""):
    return getattr(env, name, default)


def json_response(body, status=200, headers=None):
    response_headers = {"Content-Type": "application/json"}
    if headers:
        response_headers.update(headers)
    return Response(json.dumps(body), status=status, headers=response_headers)


def not_found():
    return Response("Not found", status=404)


def normalize_admin_path(value):
    path = str(value or DEFAULT_ADMIN_PATH).strip()
    if not path or path == "/":
        return DEFAULT_ADMIN_PATH
    path = path.rstrip("/")
    return path if path.startswith("/") else f"/{path}"


def get_cookie(cookie_header, name):
    for entry in str(cookie_header).split(";"):
        entry = entry.strip()
        if entry.startswith(f"{name}="):
            return entry[len(name) + 1 :]
    return ""


def text_to_html(value):
    return html.escape(str(value)).replace("\n", "<br>")


def base64_url_encode(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def base64_url_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


async def provider_error(response):
    text = await response.text()
    return text or f"Email provider returned {response.status}"
