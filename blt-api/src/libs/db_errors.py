"""Map known D1/SQLite errors to safe API responses."""

from typing import Any, Optional

from utils import error_response


def database_error_response(exc: Exception) -> Optional[Any]:
    """Return a user-facing response for expected database errors."""
    message = str(exc)
    normalized = message.lower()

    if "no such table" in normalized:
        return error_response("Database schema is not ready. Run migrations.", status=503)

    if "unique constraint failed" in normalized:
        if "hackathons.created_by_user_id, hackathons.slug" in normalized:
            return error_response("Hackathon slug already exists for this account", status=409)
        if "hackathon_registrations" in normalized:
            return error_response("Email is already registered for this hackathon", status=409)
        return error_response("Record already exists", status=409)

    if (
        "check constraint failed" in normalized
        or "not null constraint failed" in normalized
        or "foreign key constraint failed" in normalized
    ):
        return error_response("Request violates database constraints", status=400)

    return None
