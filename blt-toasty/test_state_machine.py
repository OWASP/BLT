"""
Tests for the D1 state machine using mocked Cloudflare Workers D1 environment.
"""

import pytest
from src.state_machine import transition_state, get_event, quarantine_event, VALID_TRANSITIONS
from src.errors import StateTransitionError


class MockD1Result:
    def __init__(self, changes=1, result=None):
        self.meta = {"changes": changes}
        self.result = result

    async def first(self):
        return self.result


class MockD1Statement:
    def __init__(self, db, query):
        self.db = db
        self.query = query
        self.bound_params = None

    def bind(self, *args):
        self.bound_params = args
        return self

    async def run(self):
        return MockD1Result(changes=self.db.next_changes)

    async def first(self):
        if self.db.next_event is None:
            return None
        return self.db.next_event


class MockD1Database:
    def __init__(self):
        self.next_changes = 1
        self.next_event = None
        self.statements_executed = []

    def prepare(self, query):
        stmt = MockD1Statement(self, query)
        self.statements_executed.append(stmt)
        return stmt


@pytest.fixture
def mock_db():
    return MockD1Database()


@pytest.mark.asyncio
async def test_get_event_success(mock_db):
    """Test getting an event successfully."""
    expected_event = {"id": "test_id", "status": "pending"}
    mock_db.next_event = expected_event

    event = await get_event(mock_db, "test_id")
    assert event == expected_event

    # Verify statement
    stmt = mock_db.statements_executed[0]
    assert "SELECT * FROM triage_events" in stmt.query
    assert stmt.bound_params == ("test_id",)


@pytest.mark.asyncio
async def test_get_event_not_found(mock_db):
    """Test getting an event that doesn't exist."""
    mock_db.next_event = None

    with pytest.raises(KeyError) as exc:
        await get_event(mock_db, "test_id")
    assert "not found" in str(exc.value)


@pytest.mark.asyncio
async def test_valid_transitions(mock_db):
    """Test all valid state transitions."""
    for from_state, to_states in VALID_TRANSITIONS.items():
        for to_state in to_states:
            mock_db.next_event = {"id": "test_id", "status": from_state}
            mock_db.next_changes = 1
            mock_db.statements_executed.clear()

            await transition_state(mock_db, "test_id", to_state)

            # Verify update statement
            stmt = mock_db.statements_executed[1]  # [0] is SELECT, [1] is UPDATE
            assert "UPDATE triage_events" in stmt.query
            assert stmt.bound_params == (to_state, "test_id", from_state)


@pytest.mark.asyncio
async def test_invalid_transitions(mock_db):
    """Test invalid state transitions raise StateTransitionError."""
    # pending cannot go straight to embedded
    mock_db.next_event = {"id": "test_id", "status": "pending"}

    with pytest.raises(StateTransitionError) as exc:
        await transition_state(mock_db, "test_id", "embedded")
    assert "Invalid transition" in str(exc.value)


@pytest.mark.asyncio
async def test_concurrent_modification(mock_db):
    """Test optimistic concurrency control (rowsAffected = 0)."""
    mock_db.next_event = {"id": "test_id", "status": "pending"}
    # Simulate another worker updating the row first
    mock_db.next_changes = 0

    with pytest.raises(StateTransitionError) as exc:
        await transition_state(mock_db, "test_id", "redaction_passed")
    assert "Concurrent modification detected" in str(exc.value)


@pytest.mark.asyncio
async def test_terminal_state(mock_db):
    """Test transitioning out of a terminal state fails."""
    mock_db.next_event = {"id": "test_id", "status": "exported"}

    with pytest.raises(StateTransitionError) as exc:
        await transition_state(mock_db, "test_id", "quarantined")
    assert "Invalid transition" in str(exc.value)


@pytest.mark.asyncio
async def test_quarantine_event(mock_db):
    """Test quarantining an event inserts into the audit log."""
    mock_db.next_event = {"id": "test_id", "status": "pending"}
    mock_db.next_changes = 1

    await quarantine_event(mock_db, "test_id", "test reason")

    # Should have executed SELECT, UPDATE (state transition), INSERT (audit log)
    assert len(mock_db.statements_executed) == 3

    insert_stmt = mock_db.statements_executed[2]
    assert "INSERT INTO triage_audit_log" in insert_stmt.query
    assert insert_stmt.bound_params[1] == "test_id"
    assert insert_stmt.bound_params[2] == "quarantine"
    assert insert_stmt.bound_params[3] == "test reason"
