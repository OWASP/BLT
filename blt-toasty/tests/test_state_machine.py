import pytest
from unittest.mock import MagicMock, AsyncMock

from src.state_machine import quarantine_event, StateTransitionError


@pytest.mark.asyncio
async def test_quarantine_event_zero_changes():
    db = MagicMock()
    # Mock get_event to return pending
    mock_stmt_first = AsyncMock(return_value={"status": "pending"})

    # Mock update statement to return 0 changes
    class AttrMeta:
        changes = 0

    class AttrResult:
        meta = AttrMeta()

    mock_stmt_run_0 = AsyncMock(return_value=AttrResult())

    # Mock audit statement
    mock_stmt_run_audit = AsyncMock()

    def prepare_side_effect(query):
        stmt = MagicMock()
        if "SELECT * FROM triage_events" in query:
            stmt.bind = MagicMock(return_value=stmt)
            stmt.first = mock_stmt_first
        elif "UPDATE triage_events" in query:
            stmt.bind = MagicMock(return_value=stmt)
            stmt.run = mock_stmt_run_0
        elif "INSERT INTO triage_audit_log" in query:
            stmt.bind = MagicMock(return_value=stmt)
            stmt.run = mock_stmt_run_audit
        return stmt

    db.prepare = MagicMock(side_effect=prepare_side_effect)

    with pytest.raises(StateTransitionError, match="Concurrent modification detected"):
        await quarantine_event(db, "evt-123", "test reason", has_vector=False)

    # Ensure the audit log was NOT inserted because changes was 0
    mock_stmt_run_audit.assert_not_called()
