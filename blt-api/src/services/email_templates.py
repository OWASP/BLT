"""HTML email templates loader for BLT API.

Clean separation of templates and code - templates are stored as external HTML files.
"""

from pathlib import Path
from html import escape
import os


# Get the templates directory path
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _e(value) -> str:
    """Escape dynamic content for safe insertion into HTML templates."""
    return escape(str(value), quote=True)


def load_template(template_name: str, safe_vars: list = None, **kwargs) -> str:
    """
    Load an HTML template file and replace placeholders with provided values.
    
    Placeholders use [[variable]] syntax to avoid conflicts with CSS braces.
    
    Args:
        template_name: Name of the template file (e.g., 'verification.html')
        safe_vars: List of variable names that should NOT be HTML-escaped (e.g., ['content'])
        **kwargs: Key-value pairs to replace in the template
    
    Returns:
        Rendered HTML string with placeholders replaced
    
    Example:
        >>> load_template('verification.html', username='john', verification_link='https://...')
    """
    template_path = TEMPLATES_DIR / template_name
    
    # Read template file
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Template not found: {template_path}")
    except Exception as e:
        raise Exception(f"Error loading template {template_name}: {str(e)}")
    
    safe_vars = safe_vars or []
    
    # Replace placeholders with actual values
    # Using [[variable]] syntax to avoid conflicts with CSS {braces}
    for key, value in kwargs.items():
        placeholder = f"[[{key}]]"
        # Don't escape values that are already safe HTML (like 'content')
        if key in safe_vars:
            safe_value = str(value)
        else:
            safe_value = _e(value)
        template = template.replace(placeholder, safe_value)
    
    # Check for any unreplaced placeholders (helps catch errors)
    import re
    unreplaced = re.findall(r'\[\[(\w+)\]\]', template)
    if unreplaced:
        raise KeyError(f"Missing required template variables: {', '.join(unreplaced)}")
    
    return template


def render_in_base(content: str, title: str = "OWASP BLT") -> str:
    """
    Wrap content in the base email template layout.
    
    Args:
        content: HTML content to insert into the body (already safe HTML)
        title: Email page title
    
    Returns:
        Complete HTML email with base layout
    """
    # 'content' is safe HTML we generated, don't escape it
    return load_template('base.html', safe_vars=['content'], content=content, title=title)


def get_verification_email(username: str, verification_link: str, expires_hours: int = 24) -> str:
    """Generate email verification template.

    Args:
        username: User's username.
        verification_link: Full verification URL.
        expires_hours: Hours until link expires.

    Returns:
        HTML email content.
    """
    content = load_template(
        'verification.html',
        username=username,
        verification_link=verification_link,
        expires_hours=expires_hours
    )
    return render_in_base(content, "Verify Your Email - OWASP BLT")


def get_password_reset_email(username: str, reset_link: str, expires_hours: int = 1) -> str:
    """Generate password reset template.

    Args:
        username: User's username.
        reset_link: Full password reset URL.
        expires_hours: Hours until link expires.

    Returns:
        HTML email content.
    """
    content = load_template(
        'password_reset.html',
        username=username,
        reset_link=reset_link,
        expires_hours=expires_hours
    )
    return render_in_base(content, "Reset Your Password - OWASP BLT")


def get_welcome_email(username: str, dashboard_link: str) -> str:
    """Generate welcome email after successful verification.

    Args:
        username: User's username.
        dashboard_link: Link to user dashboard.

    Returns:
        HTML email content.
    """
    content = load_template(
        'welcome.html',
        username=username,
        dashboard_link=dashboard_link
    )
    return render_in_base(content, "Welcome to OWASP BLT")


def get_bug_submission_confirmation(username: str, bug_id: str, bug_title: str) -> str:
    """Generate bug submission confirmation email.

    Args:
        username: User's username.
        bug_id: Bug identifier.
        bug_title: Bug title/description.

    Returns:
        HTML email content.
    """
    content = load_template(
        'bug_confirmation.html',
        username=username,
        bug_id=bug_id,
        bug_title=bug_title
    )
    return render_in_base(content, "Bug Submission Confirmed - OWASP BLT")
