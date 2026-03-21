"""
Email service using SendGrid Web API v3 via the Workers fetch() API.
No external dependencies - pure Python stdlib only.
Uses fetch() when running in Cloudflare Workers; falls back to urllib for local testing.
"""

import json
import base64
from typing import Optional, Tuple
import logging

from services.email_templates import (
    get_verification_email,
    get_password_reset_email,
    get_welcome_email,
    get_bug_submission_confirmation,
)

try:
    from js import fetch, Headers, Object
    _WORKERS_RUNTIME = True
except ImportError:
    fetch = None
    Headers = None
    Object = None
    _WORKERS_RUNTIME = False

_SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class EmailService:
    """SendGrid Web API v3 email service using Workers fetch()."""

    def __init__(
        self,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        from_name: str = "OWASP BLT",
    ):
        # smtp_password is the SendGrid API key; smtp_username is kept for
        # interface compatibility but SendGrid Web API only needs the key.
        self.api_key = smtp_password
        self.from_email = from_email
        self.from_name = from_name
        self.logger = logging.getLogger(__name__)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        content_type: str = "text/plain",
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> Tuple[int, str]:
        """Send an email via SendGrid Web API v3."""
        sender_address = from_email or self.from_email
        sender_name = from_name or self.from_name

        mime_type = "text/html" if content_type == "text/html" else "text/plain"
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": sender_address, "name": sender_name},
            "subject": subject,
            "content": [{"type": mime_type, "value": content}],
        }
        body = json.dumps(payload)

        headers_list = [
            ["Authorization", f"Bearer {self.api_key}"],
            ["Content-Type", "application/json"],
        ]

        try:
            if _WORKERS_RUNTIME:
                js_headers = Headers.new(headers_list)
                request_init = Object.new()
                request_init.method = "POST"
                request_init.headers = js_headers
                request_init.body = body
                response = await fetch(_SENDGRID_API_URL, request_init)
                status = response.status
                text = await response.text()
            else:
                # Local testing fallback using urllib
                import urllib.request
                req = urllib.request.Request(
                    _SENDGRID_API_URL,
                    data=body.encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req) as resp:
                        status = resp.status
                        text = resp.read().decode("utf-8")
                except urllib.error.HTTPError as http_err:
                    status = http_err.code
                    text = http_err.read().decode("utf-8")

            if status >= 400:
                self.logger.error("SendGrid error sending to %s: %s %s", to_email, status, text)
            else:
                self.logger.info("Email sent to %s (status %s)", to_email, status)
            return status, text

        except Exception as exc:
            self.logger.error("Exception sending email to %s: %s", to_email, exc)
            return 500, str(exc)

    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        verification_token: str,
        base_url: str,
        expires_hours: int = 24,
    ) -> Tuple[int, str]:
        verification_link = f"{base_url}/auth/verify-email?token={verification_token}"
        subject = "Verify your OWASP BLT account"
        html_content = get_verification_email(username, verification_link, expires_hours)
        self.logger.info("Sending verification email to %s for user %s", to_email, username)
        return await self.send_email(to_email, subject, html_content, content_type="text/html")

    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_token: str,
        base_url: str,
        expires_hours: int = 1,
    ) -> Tuple[int, str]:
        reset_link = f"{base_url}/auth/reset-password?token={reset_token}"
        subject = "Reset your OWASP BLT password"
        html_content = get_password_reset_email(username, reset_link, expires_hours)
        return await self.send_email(to_email, subject, html_content, content_type="text/html")

