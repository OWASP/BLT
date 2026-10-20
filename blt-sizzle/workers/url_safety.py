"""Outbound URL checks for user-supplied settings."""

from urllib.parse import urlparse

SLACK_WEBHOOK_HOST = "hooks.slack.com"


def is_slack_webhook_url(url):
    """True for https://hooks.slack.com/... with no credentials, port, quotes or whitespace.

    The Worker POSTs to the saved webhook URL, so anything else would let a user point it at an
    arbitrary host.
    """
    value = str(url or "").strip()
    if not value or any(ch.isspace() or ch in "\"'<>\\" for ch in value):
        return False
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() == SLACK_WEBHOOK_HOST
        and not parsed.username
        and not parsed.password
        and port is None
        and parsed.path.startswith("/services/")
    )
