"""
Email service using SendGrid SMTP via stdlib smtplib.
No external dependencies - pure Python stdlib only.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple
import logging

from services.email_templates import (
    get_verification_email,
    get_password_reset_email,
    get_welcome_email,
    get_bug_submission_confirmation,
)

_SENDGRID_HOST = "smtp.sendgrid.net"
_SENDGRID_PORT = 587


class EmailService:
    """SendGrid SMTP email service using stdlib smtplib."""

    def __init__(
        self,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        from_name: str = "OWASP BLT",
    ):
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
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
        """Send an email via SendGrid SMTP (STARTTLS on port 587)."""
        sender_address = from_email or self.from_email
        sender_name = from_name or self.from_name

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_address}>"
        msg["To"] = to_email

        mime_subtype = "html" if content_type == "text/html" else "plain"
        msg.attach(MIMEText(content, mime_subtype, "utf-8"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(_SENDGRID_HOST, _SENDGRID_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(sender_address, to_email, msg.as_string())
            self.logger.info("Email sent successfully to %s", to_email)
            return 200, "OK"
        except smtplib.SMTPAuthenticationError as exc:
            self.logger.error("SMTP auth failed: %s", exc)
            return 401, f"SMTP authentication error: {exc}"
        except Exception as exc:
            self.logger.error("Error sending email to %s: %s", to_email, exc)
            return 500, f"Error sending email: {exc}"

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

