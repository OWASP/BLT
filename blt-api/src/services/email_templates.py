"""HTML email templates for BLT API.

Professional, responsive email templates aligned with BLT branding.
"""

from html import escape


def _e(value: str) -> str:
    """Escape dynamic content inserted into HTML templates."""
    return escape(str(value), quote=True)


def get_base_template(content: str, title: str = "OWASP BLT") -> str:
    """Base email template with consistent styling.

    Args:
        content: HTML content to insert into the body.
        title: Email title.

    Returns:
        Complete HTML email string.
    """
    safe_title = _e(title)

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{safe_title}</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            width: 100% !important;
            background-color: #f5f5f5;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: #1f2937;
            line-height: 1.6;
        }}
        table {{
            border-spacing: 0;
            border-collapse: collapse;
        }}
        .wrapper {{
            width: 100%;
            background-color: #f5f5f5;
            padding: 24px 12px;
        }}
        .container {{
            width: 100%;
            max-width: 640px;
            margin: 0 auto;
            background: #ffffff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            overflow: hidden;
        }}
        .header {{
            background-color: #111827;
            border-bottom: 4px solid #e10101;
            padding: 28px 28px 22px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            color: #ffffff;
            font-size: 26px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}
        .header p {{
            margin: 6px 0 0;
            color: #d1d5db;
            font-size: 13px;
        }}
        .content {{
            padding: 30px 28px 12px;
        }}
        .content h2 {{
            margin: 0 0 14px;
            font-size: 24px;
            line-height: 1.3;
            color: #111827;
            font-weight: 700;
        }}
        .content h3 {{
            margin: 24px 0 10px;
            font-size: 18px;
            line-height: 1.4;
            color: #111827;
            font-weight: 700;
        }}
        .content p {{
            margin: 0 0 14px;
            color: #374151;
            font-size: 15px;
        }}
        .content a {{
            color: #e10101;
            text-decoration: none;
        }}
        .content a:hover {{
            text-decoration: underline;
        }}
        .button-wrap {{
            text-align: center;
            padding: 8px 0 10px;
        }}
        .button {{
            display: inline-block;
            background-color: #e10101;
            color: #ffffff !important;
            text-decoration: none;
            font-size: 15px;
            font-weight: 700;
            padding: 12px 24px;
            border-radius: 8px;
            border: 1px solid #e10101;
        }}
        .button:hover {{
            background-color: #b91c1c;
            border-color: #b91c1c;
            text-decoration: none;
        }}
        .link-box {{
            margin: 16px 0 22px;
            padding: 12px 14px;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            background-color: #fafafa;
            color: #111827;
            font-size: 13px;
            word-break: break-all;
        }}
        .info-box {{
            margin: 16px 0;
            padding: 12px 14px;
            background-color: #fef2f2;
            border-left: 4px solid #e10101;
            border-radius: 6px;
        }}
        .info-box p {{
            margin: 0;
            color: #7f1d1d;
            font-size: 14px;
        }}
        .divider {{
            height: 1px;
            background-color: #e5e5e5;
            margin: 22px 0;
        }}
        ul, ol {{
            margin: 8px 0 16px;
            padding-left: 20px;
            color: #374151;
            font-size: 15px;
        }}
        li {{
            margin: 7px 0;
        }}
        .footer {{
            padding: 20px 28px 28px;
            border-top: 1px solid #e5e5e5;
            background-color: #fafafa;
            text-align: center;
        }}
        .footer p {{
            margin: 0 0 8px;
            color: #6b7280;
            font-size: 13px;
        }}
        .footer a {{
            color: #e10101;
            text-decoration: none;
            font-weight: 600;
        }}
        .muted {{
            color: #6b7280;
            font-size: 13px;
        }}
        .small {{
            font-size: 12px;
            color: #9ca3af;
        }}
        @media only screen and (max-width: 640px) {{
            .wrapper {{
                padding: 12px 0;
            }}
            .container {{
                border-radius: 0;
                border-left: none;
                border-right: none;
            }}
            .header,
            .content,
            .footer {{
                padding-left: 18px;
                padding-right: 18px;
            }}
            .content h2 {{
                font-size: 22px;
            }}
        }}
    </style>
</head>
<body>
    <span style="display:none !important; visibility:hidden; opacity:0; color:transparent; height:0; width:0; overflow:hidden;">
        {safe_title}
    </span>

    <table role="presentation" width="100%" class="wrapper">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" class="container">
                    <tr>
                        <td class="header">
                            <h1>OWASP BLT</h1>
                            <p>Bug Logging Tool</p>
                        </td>
                    </tr>
                    <tr>
                        <td class="content">
                            {content}
                        </td>
                    </tr>
                    <tr>
                        <td class="footer">
                            <p><strong>OWASP Bug Logging Tool</strong></p>
                            <p>Making the web more secure, one report at a time.</p>
                            <p>
                                <a href="https://owaspblt.org">Website</a>
                                &nbsp;|&nbsp;
                                <a href="https://github.com/OWASP-BLT">GitHub</a>
                                &nbsp;|&nbsp;
                                <a href="https://owasp.org">OWASP</a>
                            </p>
                            <p class="small">This is an automated message. Please do not reply to this email.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def get_verification_email(username: str, verification_link: str, expires_hours: int = 24) -> str:
    """Generate email verification template.

    Args:
        username: User's username.
        verification_link: Full verification URL.
        expires_hours: Hours until link expires.

    Returns:
        HTML email content.
    """
    safe_username = _e(username)
    safe_verification_link = _e(verification_link)

    content = f"""
        <h2>Verify your email address</h2>
        <p>Hello <strong>{safe_username}</strong>,</p>
        <p>Thanks for registering with OWASP BLT. Confirm your email address to activate your account.</p>

        <div class="button-wrap">
            <a href="{safe_verification_link}" class="button">Verify Email</a>
        </div>

        <div class="info-box">
            <p><strong>Important:</strong> This verification link expires in {expires_hours} hours.</p>
        </div>

        <p class="muted">If the button does not work, copy and paste this link into your browser:</p>
        <div class="link-box">{safe_verification_link}</div>

        <div class="divider"></div>

        <p class="muted">If you did not create an OWASP BLT account, you can safely ignore this email.</p>
    """
    return get_base_template(content, "Verify Your Email - OWASP BLT")


def get_password_reset_email(username: str, reset_link: str, expires_hours: int = 1) -> str:
    """Generate password reset template.

    Args:
        username: User's username.
        reset_link: Full password reset URL.
        expires_hours: Hours until link expires.

    Returns:
        HTML email content.
    """
    safe_username = _e(username)
    safe_reset_link = _e(reset_link)

    content = f"""
        <h2>Password reset request</h2>
        <p>Hello <strong>{safe_username}</strong>,</p>
        <p>We received a request to reset your OWASP BLT password.</p>

        <div class="button-wrap">
            <a href="{safe_reset_link}" class="button">Reset Password</a>
        </div>

        <div class="info-box">
            <p><strong>Security notice:</strong> This link expires in {expires_hours} hour(s).</p>
        </div>

        <p class="muted">If the button does not work, copy and paste this link into your browser:</p>
        <div class="link-box">{safe_reset_link}</div>

        <div class="divider"></div>

        <p class="muted">
            If you did not request a password reset, no action is required and your password remains unchanged.
        </p>
    """
    return get_base_template(content, "Reset Your Password - OWASP BLT")


def get_welcome_email(username: str, dashboard_link: str) -> str:
    """Generate welcome email after successful verification.

    Args:
        username: User's username.
        dashboard_link: Link to user dashboard.

    Returns:
        HTML email content.
    """
    safe_username = _e(username)
    safe_dashboard_link = _e(dashboard_link)

    content = f"""
        <h2>Welcome to OWASP BLT</h2>
        <p>Hello <strong>{safe_username}</strong>,</p>
        <p>Your email has been verified and your account is now active.</p>

        <h3>What you can do next</h3>
        <ul>
            <li>Submit vulnerability reports.</li>
            <li>Track review status and feedback.</li>
            <li>Earn points on the leaderboard.</li>
            <li>Participate in the security community.</li>
        </ul>

        <div class="button-wrap">
            <a href="{safe_dashboard_link}" class="button">Open Dashboard</a>
        </div>

        <div class="info-box">
            <p><strong>Tip:</strong> Complete your profile to unlock all contributor features.</p>
        </div>

        <p>Thank you for helping improve security across the web.</p>
    """
    return get_base_template(content, "Welcome to OWASP BLT")


def get_bug_submission_confirmation(username: str, bug_id: str, bug_title: str) -> str:
    """Generate bug submission confirmation email.

    Args:
        username: User's username.
        bug_id: Bug identifier.
        bug_title: Bug title/description.

    Returns:
        HTML email content.
    """
    safe_username = _e(username)
    safe_bug_id = _e(bug_id)
    safe_bug_title = _e(bug_title)

    content = f"""
        <h2>Bug submission received</h2>
        <p>Hello <strong>{safe_username}</strong>,</p>
        <p>Thank you for reporting a security issue to OWASP BLT. Your submission has been recorded.</p>

        <div class="info-box">
            <p><strong>Bug ID:</strong> #{safe_bug_id}</p>
            <p><strong>Title:</strong> {safe_bug_title}</p>
            <p><strong>Status:</strong> Under review</p>
        </div>

        <h3>What happens next</h3>
        <ol>
            <li>Our security team reviews your submission.</li>
            <li>The issue is validated and prioritized.</li>
            <li>Points are awarded based on severity and impact.</li>
            <li>You receive updates as review progresses.</li>
        </ol>

        <p>We appreciate your contribution to responsible disclosure.</p>
    """
    return get_base_template(content, "Bug Submission Confirmed - OWASP BLT")
