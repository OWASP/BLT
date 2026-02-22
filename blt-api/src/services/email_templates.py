"""
HTML email templates for BLT API
Professional, responsive email templates for various use cases
"""

def get_base_template(content: str, title: str = "OWASP BLT") -> str:
    """
    Base email template with consistent styling.
    
    Args:
        content: HTML content to insert into the body
        title: Email title
    
    Returns:
        Complete HTML email string
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{title}</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f4f4f4;
            color: #333333;
            line-height: 1.6;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            color: #ffffff;
            font-size: 28px;
            font-weight: 600;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .content h2 {{
            color: #333333;
            font-size: 24px;
            margin-top: 0;
            margin-bottom: 20px;
        }}
        .content p {{
            color: #555555;
            font-size: 16px;
            margin: 15px 0;
        }}
        .button {{
            display: inline-block;
            padding: 14px 30px;
            margin: 25px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 16px;
            text-align: center;
        }}
        .button:hover {{
            background: linear-gradient(135deg, #5568d3 0%, #653b8a 100%);
        }}
        .footer {{
            background-color: #f9f9f9;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #e0e0e0;
        }}
        .footer p {{
            margin: 5px 0;
            color: #888888;
            font-size: 14px;
        }}
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
        .divider {{
            height: 1px;
            background-color: #e0e0e0;
            margin: 30px 0;
        }}
        .info-box {{
            background-color: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .info-box p {{
            margin: 5px 0;
            font-size: 14px;
            color: #666666;
        }}
        @media only screen and (max-width: 600px) {{
            .content {{
                padding: 30px 20px;
            }}
            .header h1 {{
                font-size: 24px;
            }}
            .content h2 {{
                font-size: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>OWASP BLT</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p><strong>OWASP Bug Logging Tool</strong></p>
            <p>Making the web more secure, one bug at a time.</p>
            <p>
                <a href="https://owaspblt.org">Visit Website</a> | 
                <a href="https://github.com/OWASP-BLT">GitHub</a> | 
                <a href="https://owaspblt.org">OWASP</a>
            </p>
            <p style="margin-top: 20px; font-size: 12px; color: #999999;">
                This is an automated message. Please do not reply to this email.
            </p>
        </div>
    </div>
</body>
</html>
"""


def get_verification_email(username: str, verification_link: str, expires_hours: int = 24) -> str:
    """
    Generate email verification template.
    
    Args:
        username: User's username
        verification_link: Full verification URL
        expires_hours: Hours until link expires
    
    Returns:
        HTML email content
    """
    content = f"""
        <h2>Welcome to OWASP BLT! 👋</h2>
        <p>Hi <strong>{username}</strong>,</p>
        <p>Thank you for registering with OWASP Bug Logging Tool!</p>
        <p>To get started and activate your account, please verify your email address by clicking the button below:</p>
        
        <div style="text-align: center;">
            <a href="{verification_link}" class="button">Verify Email Address</a>
        </div>
        
        <div class="info-box">
            <p><strong>⏰ Important:</strong> This verification link will expire in {expires_hours} hours.</p>
        </div>
        
        <p>If the button doesn't work, copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #667eea;">{verification_link}</p>
        
        <div class="divider"></div>
        
        <p style="font-size: 14px; color: #888888;">
            If you didn't create an account with OWASP BLT, you can safely ignore this email.
        </p>
    """
    return get_base_template(content, "Verify Your Email - OWASP BLT")


def get_password_reset_email(username: str, reset_link: str, expires_hours: int = 1) -> str:
    """
    Generate password reset template.
    
    Args:
        username: User's username
        reset_link: Full password reset URL
        expires_hours: Hours until link expires
    
    Returns:
        HTML email content
    """
    content = f"""
        <h2>Password Reset Request 🔐</h2>
        <p>Hi <strong>{username}</strong>,</p>
        <p>We received a request to reset your password for your OWASP BLT account.</p>
        <p>Click the button below to create a new password:</p>
        
        <div style="text-align: center;">
            <a href="{reset_link}" class="button">Reset Password</a>
        </div>
        
        <div class="info-box">
            <p><strong>⏰ Important:</strong> This password reset link will expire in {expires_hours} hour(s) for security reasons.</p>
        </div>
        
        <p>If the button doesn't work, copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #667eea;">{reset_link}</p>
        
        <div class="divider"></div>
        
        <p style="font-size: 14px; color: #888888;">
            If you didn't request a password reset, please ignore this email or contact support if you have concerns.
            Your password will remain unchanged.
        </p>
    """
    return get_base_template(content, "Reset Your Password - OWASP BLT")


def get_welcome_email(username: str, dashboard_link: str) -> str:
    """
    Generate welcome email after successful verification.
    
    Args:
        username: User's username
        dashboard_link: Link to user dashboard
    
    Returns:
        HTML email content
    """
    content = f"""
        <h2>Welcome to OWASP BLT! 🎉</h2>
        <p>Hi <strong>{username}</strong>,</p>
        <p>Your email has been verified successfully! Welcome to the OWASP Bug Logging Tool community.</p>
        
        <h3 style="color: #667eea; margin-top: 30px;">What's Next?</h3>
        <ul style="color: #555555; font-size: 16px; line-height: 1.8;">
            <li>🔍 Start reporting security vulnerabilities</li>
            <li>🏆 Earn points and climb the leaderboard</li>
            <li>🤝 Join our community of security researchers</li>
            <li>📚 Learn from other security experts</li>
        </ul>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="{dashboard_link}" class="button">Go to Dashboard</a>
        </div>
        
        <div class="info-box" style="margin-top: 30px;">
            <p><strong>💡 Pro Tip:</strong> Complete your profile to unlock all features and start contributing to the community!</p>
        </div>
        
        <p style="margin-top: 30px;">Happy bug hunting! 🐛</p>
    """
    return get_base_template(content, "Welcome to OWASP BLT")


def get_bug_submission_confirmation(username: str, bug_id: str, bug_title: str) -> str:
    """
    Generate bug submission confirmation email.
    
    Args:
        username: User's username
        bug_id: Bug identifier
        bug_title: Bug title/description
    
    Returns:
        HTML email content
    """
    content = f"""
        <h2>Bug Submission Received ✅</h2>
        <p>Hi <strong>{username}</strong>,</p>
        <p>Thank you for submitting a security vulnerability to OWASP BLT!</p>
        
        <div class="info-box">
            <p><strong>Bug ID:</strong> #{bug_id}</p>
            <p><strong>Title:</strong> {bug_title}</p>
            <p><strong>Status:</strong> Under Review</p>
        </div>
        
        <p>Our team will review your submission shortly. You'll receive a notification once the review is complete.</p>
        
        <h3 style="color: #667eea; margin-top: 30px;">What Happens Next?</h3>
        <ol style="color: #555555; font-size: 16px; line-height: 1.8;">
            <li>Our security team reviews your submission</li>
            <li>We validate the vulnerability</li>
            <li>Points are awarded based on severity</li>
            <li>You receive feedback and updates</li>
        </ol>
        
        <p style="margin-top: 30px;">Thank you for helping make the web more secure! 🛡️</p>
    """
    return get_base_template(content, "Bug Submission Confirmed - OWASP BLT")
