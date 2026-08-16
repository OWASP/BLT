"""
State machine for Toasty Cloudflare Worker triage events.

Enforces strict state transitions using optimistic concurrency control
with Cloudflare D1.
"""

import logging
import secrets

from src.errors import StateTransitionError

logger = logging.getLogger("toasty.state_machine")

VALID_TRANSITIONS = {
    "pending": ["redaction_passed", "redaction_failed", "quarantined"],
    "redaction_passed": ["summarized", "quarantined"],
    "redaction_failed": ["quarantined"],
    "summarized": ["embedded", "quarantined"],
    "embedded": ["exported", "quarantined"],
    "exported": [],
    "quarantined": [],
}


async def get_event(db, event_id: str) -> dict:
    """
    Fetch a triage event by its ID.

    Args:
        db: The D1 database binding.
        event_id (str): The ID of the triage event.

    Returns:
        dict: The event details.

    Raises:
        KeyError: If the event is not found.
    """
    query = "SELECT * FROM triage_events WHERE id = ?"
    stmt = db.prepare(query).bind(event_id)
    result = await stmt.first()

    # In Pyodide D1 client, if result is None, the record was not found.
    if result is None:
        raise KeyError(f"Event with id {event_id} not found")

    # Depending on the Pyodide/D1 client version, result might be a dict-like object
    # If it has a .to_py() method (like JS Map/Object), we'd call it, but D1 usually
    # returns a direct object we can cast to dict or treat as dict.
    if hasattr(result, "to_py"):
        return result.to_py()
    return dict(result)


async def transition_state(db, event_id: str, to_status: str, env=None) -> None:
    """
    Transition an event to a new state using optimistic concurrency control.
    If transitioning to 'exported', emits telemetry to Cloudflare Analytics Engine.

    Args:
        db: The D1 database binding.
        event_id (str): The ID of the triage event.
        to_status (str): The desired new state.
        env: The Cloudflare Worker environment (optional, used for analytics).

    Raises:
        StateTransitionError: If the transition is invalid or a concurrent modification occurs.
        KeyError: If the event is not found.
    """
    event = await get_event(db, event_id)
    current_status = event["status"]

    if to_status not in VALID_TRANSITIONS.get(current_status, []):
        raise StateTransitionError(f"Invalid transition from {current_status} to {to_status}")

    query = "UPDATE triage_events SET status = ?, updated_at = datetime('now') WHERE id = ? AND status = ?"
    stmt = db.prepare(query).bind(to_status, event_id, current_status)
    result = await stmt.run()

    # Access meta data for rows changed
    # Depending on D1 client, meta might be result.meta or result["meta"]
    meta = result.meta if hasattr(result, "meta") else (result.get("meta", {}) if isinstance(result, dict) else {})
    if hasattr(meta, "changes"):
        changes = meta.changes
    elif isinstance(meta, dict):
        changes = meta.get("changes", 0)
    else:
        changes = 0

    if changes == 0:
        raise StateTransitionError("Concurrent modification detected")

    if to_status == "exported" and env is not None:
        analytics = getattr(env, "ANALYTICS", None)
        if analytics:
            try:
                # We need to calculate duration. The event we fetched has created_at
                created_at_str = event.get("created_at")
                project_id = event.get("project_id", 0)

                # Use SQL to compute duration correctly using julianday with subsecond precision
                dur_query = "SELECT (julianday('now') - julianday(?)) * 86400 AS duration"
                dur_res = await db.prepare(dur_query).bind(created_at_str).first()
                duration = dur_res.get("duration", 0) if dur_res else 0

                analytics.writeDataPoint(
                    {"blobs": [str(project_id), "exported"], "doubles": [float(duration)], "indexes": [event_id]}
                )
            except Exception as exc:
                logger.error(f"Failed to emit telemetry: {exc}")


async def quarantine_event(db, event_id: str, reason: str, env=None, has_vector: bool = True) -> None:
    """
    Quarantine an event and log the reason to the audit log.
    If has_vector is True, deletes the associated vector from Vectorize and requires env.VECTORIZE.

    Args:
        db: The D1 database binding.
        event_id (str): The ID of the triage event.
        reason (str): The reason for quarantining the event.
        env: The Cloudflare Worker environment (optional if has_vector=False).
        has_vector: Whether the event has been vectorized and needs cleanup.

    Raises:
        StateTransitionError: If the transition is invalid or a concurrent modification occurs.
    """
    # 1. Fetch current state to enforce valid transitions and concurrency control
    event = await get_event(db, event_id)
    current_status = event["status"]

    if "quarantined" not in VALID_TRANSITIONS.get(current_status, []):
        raise StateTransitionError(f"Invalid transition from {current_status} to quarantined")

    # 2. Prepare statements
    audit_id = secrets.token_hex(16)

    stmt_update = db.prepare(
        "UPDATE triage_events SET status = 'quarantined', quarantine_reason = ?, updated_at = datetime('now') WHERE id = ? AND status = ?"
    ).bind(reason, event_id, current_status)

    stmt_audit = db.prepare("INSERT INTO triage_audit_log (id, event_id, action, reason) VALUES (?, ?, ?, ?)").bind(
        audit_id, event_id, "quarantine", reason
    )

    # 3. Execute update and audit log insertion atomically in a single batch
    results = await db.batch([stmt_update, stmt_audit])

    result_update = results[0]

    meta = (
        result_update.meta
        if hasattr(result_update, "meta")
        else (result_update.get("meta", {}) if isinstance(result_update, dict) else {})
    )
    if hasattr(meta, "changes"):
        changes = meta.changes
    elif isinstance(meta, dict):
        changes = meta.get("changes", 0)
    else:
        changes = 0

    if changes == 0:
        raise StateTransitionError("Concurrent modification detected")

    # 3. Explicitly purge the vector payload if it has one
    if has_vector:
        if not env or not hasattr(env, "VECTORIZE"):
            raise ValueError("env.VECTORIZE is required to cleanup a vectorized event")
        from src.vectorize_client import delete_vector

        try:
            await delete_vector(event_id, env)
        except Exception as exc:
            logger.warning("Vector cleanup failed for %s, marking pending_cleanup: %s", event_id, exc)
            await db.prepare("UPDATE triage_events SET quarantine_reason = ? WHERE id = ?").bind(
                f"{reason}; vector_cleanup_pending", event_id
            ).run()
