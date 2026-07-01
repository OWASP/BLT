"""
State machine for Toasty Cloudflare Worker triage events.

Enforces strict state transitions using optimistic concurrency control
with Cloudflare D1.
"""

from src.errors import StateTransitionError
import secrets

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


async def transition_state(db, event_id: str, to_status: str) -> None:
    """
    Transition an event to a new state using optimistic concurrency control.

    Args:
        db: The D1 database binding.
        event_id (str): The ID of the triage event.
        to_status (str): The desired new state.

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
    meta = result.meta if hasattr(result, "meta") else result.get("meta", {})
    changes = getattr(meta, "changes", meta.get("changes", 0))

    if changes == 0:
        raise StateTransitionError("Concurrent modification detected")


async def quarantine_event(db, event_id: str, reason: str) -> None:
    """
    Quarantine an event and log the reason to the audit log.

    Args:
        db: The D1 database binding.
        event_id (str): The ID of the triage event.
        reason (str): The reason for quarantining the event.

    Raises:
        StateTransitionError: If the transition is invalid or a concurrent modification occurs.
    """
    # 1. Update the state to quarantined (this will enforce valid transitions)
    await transition_state(db, event_id, "quarantined")

    # 2. Insert into the audit log
    audit_id = secrets.token_hex(16)
    query = "INSERT INTO triage_audit_log (id, event_id, action, reason) VALUES (?, ?, ?, ?)"
    stmt = db.prepare(query).bind(audit_id, event_id, "quarantine", reason)
    await stmt.run()
