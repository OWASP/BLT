"""Helpers for user-owned API handlers."""

from typing import Any, Optional


def get_request_user_id(request: Any) -> Optional[int]:
    """Return the user id attached by generated user API-key validation."""
    value = getattr(request, "user_id", None)
    if value is None:
        return None

    try:
        user_id = int(value)
    except (TypeError, ValueError):
        return None

    return user_id if user_id > 0 else None
