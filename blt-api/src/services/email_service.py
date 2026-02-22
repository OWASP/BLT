"""
Email service using Mailgun REST API directly via fetch.
No external dependencies - works with Cloudflare Workers/Pyodide.
"""

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

    # curl -s --user 'api:YOUR_API_KEY' \
    # https://api.mailgun.net/v3/YOUR_DOMAIN_NAME/messages \
    # -F from='Excited User <postmaster@YOUR_DOMAIN_NAME>' \
    # -F to=recipient@example.com \
    # -F subject="Hello there!" \
    # -F text='This will be the text-only version' \
    # --form-string html='<html><body><p>This is the HTML version</p></body></html>'


class EmailService:
    """
    Mailgun email service using direct HTTP API calls.
    
    Supports both:
    - Sandbox domain (testing only - requires authorized recipients)
    - Custom domain (production - can send to anyone after DNS verification)
    """
    
    MAILGUN_API_URL = "https://api.mailgun.net"
    
    def __init__(
        self, 
        api_key: str, 
        domain: str,
        from_email: str = None, 
        from_name: str = "OWASP BLT"
    ):
        """
        Initialize EmailService.
        
        Args:
            api_key: Mailgun API key (Private API Key or Sending API Key)
            domain: Your Mailgun domain 
                   - Sandbox: "sandbox123...mailgun.org" (testing only)
                   - Custom: "yourdomain.com" or "mg.yourdomain.com" (production)
            from_email: Default sender email (if None, uses postmaster@domain)
            from_name: Default sender name
        """
        self.api_key = api_key
        self.domain = domain
        self.from_email = from_email or f"postmaster@{domain}"
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
        Send an email using Mailgun API.
        
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
        # Prepare form data for Mailgun API
        from_address = from_email or self.from_email
        sender_name = from_name or self.from_name
        from_field = f"{sender_name} <{from_address}>"
        
        # Build form data as URL-encoded string
        form_data = {
            "from": from_field,
            "to": to_email,
            "subject": subject,
        }
        
        # Add content based on type
        if content_type == "text/html":
            form_data["html"] = content
        else:
            form_data["text"] = content
        
        # URL encode the form data
        encoded_data = "&".join([f"{k}={self._url_encode(v)}" for k, v in form_data.items()])
        
        # Prepare Basic Auth (api:YOUR_API_KEY)
        import base64
        auth_string = f"api:{self.api_key}"
        auth_bytes = auth_string.encode('ascii')
        base64_auth = base64.b64encode(auth_bytes).decode('ascii')
        
        # Prepare headers as a list of tuples for JavaScript Headers API
        headers_list = [
            ["Authorization", f"Basic {base64_auth}"],
            ["Content-Type", "application/x-www-form-urlencoded"]
        ]
        
        try:
            # Make HTTP request using Cloudflare Workers fetch
            if Headers:
                js_headers = Headers.new(headers_list)
                
                # Create the request init object using JavaScript Object
                from js import Object
                request_init = Object.new()
                request_init.method = "POST"
                request_init.headers = js_headers
                request_init.body = encoded_data
                
                response = await fetch(f"{self.MAILGUN_API_URL}/v3/{self.domain}/messages", request_init)
            else:
                # Fallback for testing
                response = await fetch(
                    f"{self.MAILGUN_API_URL}/v3/{self.domain}/messages",
                    {
                        "method": "POST",
                        "headers": {
                            "Authorization": f"Basic {base64_auth}",
                            "Content-Type": "application/x-www-form-urlencoded"
                        },
                        "body": encoded_data
                    }
                )
            
            status = response.status
            text = await response.text()
            
            if status >= 400:
                self.logger.error(f"Failed to send email to {to_email}: {status} - {text}")
            else:
                self.logger.info(f"Email sent successfully to {to_email} with status {status}")
            
            return status, text
        
            
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return 500, f"Error sending email: {str(e)}"
    
    def _url_encode(self, value: str) -> str:
        """URL encode a string value."""
        import urllib.parse
        return urllib.parse.quote(str(value), safe='')
    
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

