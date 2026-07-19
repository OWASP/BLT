"""GitLab webhook ingestion helpers (VF01).

Used by the FastAPI route handler. Keeps the route thin and testable.
"""

from __future__ import annotations

from typing import Any

from ..core.security import verify_token


def verify_gitlab_signature(provided_token: str | None, expected_secret: str | None) -> bool:
    """Return True iff the GitLab webhook token matches the configured secret."""
    return verify_token(provided_token, expected_secret)


def parse_event_type(headers: dict[str, str], payload: dict[str, Any]) -> str:
    """Extract the GitLab event type from the X-Gitlab-Event header.

    Falls back to ``payload['object_kind']`` if the header is absent.
    """
    header_value = headers.get("x-gitlab-event") or headers.get("X-Gitlab-Event")
    if header_value:
        return header_value
    return str(payload.get("object_kind", "unknown"))


def is_supported_event(event_name: str) -> bool:
    """Return True if the event name maps to one of our internal types."""
    supported = {
        "Push Hook",
        "Issue Hook",
        "Merge Request Hook",
        "Note Hook",
        "Pipeline Hook",
        "Job Hook",
        "Tag Push Hook",
    }
    return event_name in supported