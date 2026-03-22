"""HTML template rendering for BLT-Lettuce."""

from pathlib import Path

_TEMPLATE_CACHE = {}
_TEMPLATES_DIR = Path(__file__).with_name("templates")


def _load_template(template_name):
    """Load and cache a template file by name."""
    if template_name not in _TEMPLATE_CACHE:
        template_path = _TEMPLATES_DIR / template_name
        _TEMPLATE_CACHE[template_name] = template_path.read_text(encoding="utf-8")
    return _TEMPLATE_CACHE[template_name]


def _render_template(template_name, replacements):
    """Render a template by replacing {{ token }} placeholders with values."""
    rendered = _load_template(template_name)
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))
    return rendered


def html_escape(text):
    """Escape HTML special characters to prevent XSS."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def get_homepage_html(user=None):
    """Generate the homepage HTML."""
    auth_button_href = "/workspace/add"
    auth_button_text = "Connect Workspace"

    return _render_template(
        "homepage.html",
        {
            "AUTH_BUTTON_HREF": auth_button_href,
            "AUTH_BUTTON_TEXT": auth_button_text,
        },
    )


def _status_item(name, description, value, required):
    """Render one environment variable status row for the status page."""
    raw_value = str(value or "").strip()
    is_set = bool(raw_value)

    if is_set:
        status_chip = '<span class="inline-flex items-center gap-1 rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs font-semibold"><i class="fas fa-check"></i> Set</span>'
        preview = f'<code class="text-xs text-gray-500">{html_escape(raw_value[:12])}...</code>'
        card_class = "status-item set border-green-200"
    else:
        level = "Required" if required else "Optional"
        status_chip = (
            '<span class="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-semibold">'
            f'<i class="fas fa-triangle-exclamation"></i> Missing ({level})'
            "</span>"
        )
        preview = '<span class="text-xs text-gray-400">Not configured</span>'
        card_class = "status-item missing border-red-200"

    return (
        f'<div class="{card_class} border rounded-lg p-3">'
        '<div class="flex items-start justify-between gap-3">'
        "<div>"
        f'<p class="text-sm font-semibold text-gray-800">{html_escape(name)}</p>'
        f'<p class="text-xs text-gray-500">{html_escape(description)}</p>'
        "</div>"
        f"{status_chip}"
        "</div>"
        f'<div class="mt-2">{preview}</div>'
        "</div>"
    )


def get_status_html(env):
    """Generate HTML status page with environment configuration checks."""
    slack_token = getattr(env, "SLACK_TOKEN", None)
    signing_secret = getattr(env, "SIGNING_SECRET", None)
    slack_client_id = getattr(env, "SLACK_CLIENT_ID", None)
    slack_client_secret = getattr(env, "SLACK_CLIENT_SECRET", None)
    sentry_dsn = getattr(env, "SENTRY_DSN", None)
    base_url = getattr(env, "BASE_URL", None)
    joins_channel = getattr(env, "JOINS_CHANNEL_ID", None)
    contribute_id = getattr(env, "CONTRIBUTE_ID", None)

    replacements = {
        "SLACK_TOKEN_STATUS": _status_item(
            "SLACK_TOKEN",
            "Slack Bot User OAuth Token (xoxb-...) for API calls",
            slack_token,
            required=True,
        ),
        "SIGNING_SECRET_STATUS": _status_item(
            "SIGNING_SECRET",
            "Slack App Signing Secret for webhook verification",
            signing_secret,
            required=True,
        ),
        "SLACK_CLIENT_ID_STATUS": _status_item(
            "SLACK_CLIENT_ID",
            "Slack OAuth App Client ID for user authentication",
            slack_client_id,
            required=True,
        ),
        "SLACK_CLIENT_SECRET_STATUS": _status_item(
            "SLACK_CLIENT_SECRET",
            "Slack OAuth App Client Secret for token exchange",
            slack_client_secret,
            required=True,
        ),
        "SENTRY_DSN_STATUS": _status_item(
            "SENTRY_DSN",
            "Sentry Data Source Name for error tracking",
            sentry_dsn,
            required=False,
        ),
        "BASE_URL_STATUS": _status_item(
            "BASE_URL",
            "Base URL for OAuth redirects (e.g., https://lettuce.owaspblt.org)",
            base_url,
            required=False,
        ),
        "JOINS_CHANNEL_ID_STATUS": _status_item(
            "JOINS_CHANNEL_ID",
            "Channel ID where join notifications are posted",
            joins_channel,
            required=False,
        ),
        "CONTRIBUTE_ID_STATUS": _status_item(
            "CONTRIBUTE_ID",
            "Channel ID for contribution guidelines",
            contribute_id,
            required=False,
        ),
    }

    return _render_template("status.html", replacements)


def get_404_html():
    """Generate the 404 not found HTML page."""
    return _load_template("404.html")


def get_500_html():
    """Generate the 500 internal server error HTML page."""
    return _load_template("500.html")


def get_privacy_html():
    """Generate the privacy policy HTML page."""
    return _load_template("privacy.html")
