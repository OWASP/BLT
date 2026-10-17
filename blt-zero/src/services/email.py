import json
import base64
from js import Headers, fetch


def _b64encode_attachment(data):
    if data is None:
        return None
    if not isinstance(data, (bytes, bytearray, memoryview)):
        if not isinstance(data, str):
            data = json.dumps(data)
        data = data.encode("utf-8")
    return base64.b64encode(data).decode("ascii")


async def send_email(
    env,
    to,
    subject,
    body,
    attachment_name=None,
    attachment_json=None,
    *,
    attachment_data=None,
    attachment_content_type="application/octet-stream",
):
    """
    Send email via SendGrid only.
    - Supports binary attachments (attachment_data) or JSON (attachment_json).
    """

    from_email = getattr(env, "SENDGRID_FROM_EMAIL", "no-reply@example.org")
    from_name = getattr(env, "SENDGRID_FROM_NAME", "BLT-Zero")

    api_key = getattr(env, "SENDGRID_API_KEY", None)
    if not api_key:
        raise Exception(
            "SendGrid not configured: set SENDGRID_API_KEY; optionally set SENDGRID_FROM_EMAIL/NAME."
        )

    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }

    if attachment_name and (attachment_data is not None or attachment_json is not None):
        content = _b64encode_attachment(
            attachment_data if attachment_data is not None else attachment_json
        )
        ctype = (
            attachment_content_type
            if attachment_data is not None
            else "application/json"
        )

        payload["attachments"] = [
            {
                "content": content,
                "filename": attachment_name,
                "type": ctype,
                "disposition": "attachment",
            }
        ]

    headers = Headers.new()
    headers.set("authorization", f"Bearer {api_key}")
    headers.set("content-type", "application/json")

    r = await fetch(
        "https://api.sendgrid.com/v3/mail/send",
        method="POST",
        headers=headers,
        body=json.dumps(payload),
    )

    # SendGrid returns 202 on success
    if r.status != 202:
        txt = await r.text() if hasattr(r, "text") else ""
        raise Exception(f"Email delivery failed (SendGrid): {r.status} {txt}")


async def sync_points(env, username, domain):
    """Sync points with main BLT API."""
    token = getattr(env, "MAIN_BLT_API_TOKEN", None)
    if not token:
        return

    headers = Headers.new()
    headers.set("content-type", "application/json")
    headers.set("authorization", f"Token {token}")

    try:
        await fetch(
            f"{env.MAIN_BLT_API_URL}/api/v1/zero-trust-points/",
            method="POST",
            headers=headers,
            body=json.dumps({"username": username, "domain_name": domain}),
        )
    except Exception:
        # Best-effort only: never block the submission path if BLT sync fails.
        # Intentionally avoid logging username or domain here to preserve privacy.
        return