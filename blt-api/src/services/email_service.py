"""
Email service using SendGrid REST API directly via fetch.
No external dependencies - works with Cloudflare Workers/Pyodide.
"""

import json
from typing import Optional, Tuple, Dict, Any
import logging
try:
    from js import fetch, Headers
except ImportError:
    # Mock for local testing
    fetch = None
    Headers = None


class EmailService:
    """SendGrid email service using direct HTTP API calls."""
    
    SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
    
    def __init__(self, api_key: str, from_email: str = "noreply@blt.owasp.org", from_name: str = "OWASP BLT"):
        """
        Initialize EmailService.
        
        Args:
            api_key: SendGrid API key
            from_email: Default sender email
            from_name: Default sender name
        """
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.logger = logging.getLogger("EmailService")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        content_type: str = "text/plain",
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> Tuple[int, str]:
        """
        Send an email using SendGrid API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email content/body
            content_type: Content type (text/plain or text/html)
            from_email: Sender email (uses default if not provided)
            from_name: Sender name (uses default if not provided)
        
        Returns:
            Tuple of (status_code, response_text)
        """
        # Prepare request payload
        payload = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "subject": subject
                }
            ],
            "from": {
                "email": from_email or self.from_email,
                "name": from_name or self.from_name
            },
            "content": [
                {
                    "type": content_type,
                    "value": content
                }
            ]
        }
        
        # Prepare headers as a list of tuples for JavaScript Headers API
        headers_list = [
            ["Authorization", f"Bearer {self.api_key}"],
            ["Content-Type", "application/json"]
        ]
        
        try:
            # Make HTTP request using Cloudflare Workers fetch
            # Headers.new() expects a sequence of [key, value] pairs
            if Headers:
                js_headers = Headers.new(headers_list)
            else:
                # Fallback for testing
                js_headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            
            response = await fetch(
                self.SENDGRID_API_URL,
                {
                    "method": "POST",
                    "headers": js_headers,
                    "body": json.dumps(payload)
                }
            )
            
            status = response.status
            text = await response.text()
            
            self.logger.info(f"Email sent to {to_email} with status {status}")
            
            return status, text
        
            
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return 500, f"Error sending email: {str(e)}"
    
    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        verification_token: str,
        base_url: str
    ) -> Tuple[int, str]:
        """
        Send email verification email.
        
        Args:
            to_email: Recipient email
            username: User's username
            verification_token: Email verification token
            base_url: Base URL for verification link
        
        Returns:
            Tuple of (status_code, response_text)
        """
        verification_link = f"{base_url}/verify-email?token={verification_token}"
        
        subject = "Verify your OWASP BLT account"
        content = f"""
                    Hello {username},

                    Thank you for registering with OWASP BLT!

                    Please verify your email address by clicking the link below:

                    {verification_link}

                    This link will expire in 24 hours.

                    If you didn't create an account, you can safely ignore this email.

                    Best regards,
                    OWASP BLT Team
                    """
                    
                    
        await self.send_email(to_email, subject, content)
        self.logger.info(f"Verification email sent to {to_email} for user {username}")
        return 
    
    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_token: str,
        base_url: str
    ) -> Tuple[int, str]:
        """
        Send password reset email.
        
        Args:
            to_email: Recipient email
            username: User's username
            reset_token: Password reset token
            base_url: Base URL for reset link
        
        Returns:
            Tuple of (status_code, response_text)
        """
        reset_link = f"{base_url}/reset-password?token={reset_token}"
        
        subject = "Reset your OWASP BLT password"
        content = f"""
                Hello {username},

                We received a request to reset your password for your OWASP BLT account.

                Click the link below to reset your password:

                {reset_link}

                This link will expire in 1 hour.

                If you didn't request a password reset, you can safely ignore this email.

                Best regards,
                OWASP BLT Team
                """
        
        return await self.send_email(to_email, subject, content)

