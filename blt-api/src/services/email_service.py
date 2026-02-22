"""
Email service using SendGrid REST API directly via fetch.
No external dependencies - works with Cloudflare Workers/Pyodide.
"""

import json
from typing import Optional, Tuple, Dict, Any
import logging
from services.email_templates import (
    get_verification_email,
    get_password_reset_email,
    get_welcome_email,
    get_bug_submission_confirmation
)

try:
    from js import fetch, Headers, Object
except ImportError:
    # Mock for local testing
    fetch = None
    Headers = None
    Object = None


class EmailService:
    """SendGrid email service using direct HTTP API calls."""
    
    SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
    
    def __init__(self, api_key: str, from_email: str = "kaif@post0.live", from_name: str = "OWASP BLT"):
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
        self.logger = logging.getLogger(__name__)
    
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
        
        self.logger.info("Api key ")
        
        # Prepare headers as a list of tuples for JavaScript Headers API
        headers_list = [
            ["Authorization", f"Bearer {self.api_key}"],
            ["Content-Type", "application/json"]
        ]
        
        try:
            # Make HTTP request using Cloudflare Workers fetch
            # Create Headers object properly for Cloudflare Workers
            if Headers:
                js_headers = Headers.new(headers_list)
                
                # Create the request init object using JavaScript Object
                from js import Object
                request_init = Object.new()
                request_init.method = "POST"
                request_init.headers = js_headers
                request_init.body = json.dumps(payload)
                
                response = await fetch(self.SENDGRID_API_URL, request_init)
            else:
                # Fallback for testing
                response = await fetch(
                    self.SENDGRID_API_URL,
                    {
                        "method": "POST",
                        "headers": {
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
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
        base_url: str,
        expires_hours: int = 24
    ) -> Tuple[int, str]:
        """
        Send email verification email with HTML template.
        
        Args:
            to_email: Recipient email
            username: User's username
            verification_token: Email verification token
            base_url: Base URL for verification link
            expires_hours: Hours until link expires (default: 24)
        
        Returns:
            Tuple of (status_code, response_text)
        """
        verification_link = f"{base_url}/verify-email?token={verification_token}"
        
        subject = "Verify your OWASP BLT account"
        html_content = get_verification_email(username, verification_link, expires_hours)
        
        self.logger.info(f"Verification email sent to {to_email} for user {username}")
        return await self.send_email(to_email, subject, html_content, content_type="text/html")
    
    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_token: str,
        base_url: str,
        expires_hours: int = 1
    ) -> Tuple[int, str]:
        """
        Send password reset email with HTML template.
        
        Args:
            to_email: Recipient email
            username: User's username
            reset_token: Password reset token
            base_url: Base URL for reset link
            expires_hours: Hours until link expires (default: 1)
        
        Returns:
            Tuple of (status_code, response_text)
        """
        reset_link = f"{base_url}/reset-password?token={reset_token}"
        
        subject = "Reset your OWASP BLT password"
        html_content = get_password_reset_email(username, reset_link, expires_hours)
        
        return await self.send_email(to_email, subject, html_content, content_type="text/html")

