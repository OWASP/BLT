import html
import re
from pathlib import Path


def esc(s: str) -> str:
    """Escape HTML characters."""
    return html.escape(s)

def replace_template(template: str, replacements: dict) -> str:
    """Replace {{key}} placeholders in template with values."""
    result = template
    for key, value in replacements.items():
        result = re.sub(r'\{\{' + key + r'\}\}', value, result)
    return result


def read_html_file(filename: str) -> str:
    """Read HTML file from pages directory."""
    
    # Get the directory where this file is located
    current_dir = Path(__file__).parent
    
    # Try multiple possible paths relative to various locations
    paths = [
        current_dir.parent / "pages" / filename,  # From services dir, go up to src then to pages
        current_dir.parent.parent / "src" / "pages" / filename,  # From project root
        Path("pages") / filename,  # Direct path
        Path("src/pages") / filename,  # From project root
    ]
    
    for path in paths:
        try:
            if path.exists():
                return path.read_text()
        except Exception:
            continue
    
    # If all paths fail, raise error with helpful message
    raise FileNotFoundError(f"Could not find {filename} in any of: {paths}")


def layout(title: str, body: str, include_turnstile_script: bool) -> str:
    """Wrap content in the main layout template."""
    # Read layout HTML
    layout_html = read_html_file("layout.html")
    
    turnstile_script = (
        '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>'
        if include_turnstile_script else ''
    )
    
    return replace_template(layout_html, {
        "TITLE": esc(title),
        "BODY": body,
        "TURNSTILE_SCRIPT": turnstile_script
    })

def submit_page(context: dict) -> str:
    max_files = str(context.get("maxFiles", 5))
    max_total = str(context.get("maxTotalBytes", 5242880))
    
    # 1. Read the file using your existing utility
    submit_html = read_html_file("submit.html")
    
    body = replace_template(submit_html, {
        "MAX_FILES": max_files,
        "MAX_TOTAL": max_total
    })
    
    # 3. Return wrapped in the standard layout
    return layout("BLT-Zero — Submit Encrypted Report", body, False)

def docs_security() -> str:
    """Generate the security documentation page."""
    docs_security_html = read_html_file("docs-security.html")
    
    return layout("BLT-Zero — Security Model", docs_security_html, False)


def docs_org_onboarding(app_origin: str) -> str:
    """Generate the organization onboarding documentation page."""
    docs_org_onboarding_html = read_html_file("docs-org-onboarding.html")
    
    body = replace_template(docs_org_onboarding_html, {
        "APP_ORIGIN": esc(app_origin)
    })
    
    return layout("BLT-Zero — Org Onboarding", body, False)


def docs_decrypt() -> str:
    """Generate the decryption guide page."""
    docs_decrypt_html = read_html_file("docs-decrypt.html")
    
    return layout("BLT-Zero — Decrypt Guide", docs_decrypt_html, False)


def admin_onboard_page() -> str:
    """Generate the admin onboarding page."""

    admin_onboard_html = read_html_file("admin-onboard.html")

    return layout("BLT-Zero — Org Admin Onboarding", admin_onboard_html,False)


def onboarding_email_body(app_origin: str, domain: str) -> str:
    """Generate the onboarding email body text."""
    return f"""Hello Security Team,

You have been onboarded to BLT-Zero (zero.blt.owasp.org) for domain: {domain}

How it works:
- Reporters encrypt in their browser using your public key.
- BLT-Zero receives only ciphertext and emails it to you.
- Only your private key can decrypt.

Next steps:
- Decrypt guide: {app_origin}/docs/decrypt
- Security model: {app_origin}/docs/security

Regards,
BLT-Zero Maintainers (OWASP BLT)
"""
