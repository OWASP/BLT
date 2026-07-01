"""Unit tests for the Event model."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from models.event import Event


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=None)


class TestEventConstruction:
    """Minimal valid Event creation."""

    def test_minimal_gitlab_event(self):
        event = Event(
            source="gitlab",
            event_type="mr_opened",
            actor_id="12345",
            actor_name="rudra-rps",
        )
        assert isinstance(event.id, UUID)
        assert event.source == "gitlab"
        assert event.event_type == "mr_opened"
        assert event.actor_id == "12345"
        assert event.actor_name == "rudra-rps"
        assert event.repository == ""
        assert event.metadata == {}
        assert event.contributor_id is None
        assert event.sequence_number is None

    def test_minimal_blt_event(self):
        event = Event(
            source="blt",
            event_type="bug_bounty_submitted",
            actor_id="678",
            actor_name="alice_hunter",
        )
        assert event.source == "blt"
        assert event.event_type == "bug_bounty_submitted"

    def test_full_event(self):
        ts = _utc("2026-07-15T10:22:00")
        event = Event(
            source="gitlab",
            event_type="mr_opened",
            actor_id="12345",
            actor_name="rudra-rps",
            repository="OWASP-BLT/BLT",
            timestamp=ts,
            metadata={"pr_number": 412, "title": "Add webhook ingestion layer"},
        )
        assert event.repository == "OWASP-BLT/BLT"
        assert event.timestamp == ts
        assert event.metadata["pr_number"] == 412


class TestEventValidation:
    """Validation rules on the Event model."""

    def test_source_must_be_gitlab_or_blt(self):
        with pytest.raises(ValidationError, match="source"):
            Event(
                source="github",  # no longer valid
                event_type="issue_opened",
                actor_id="1",
                actor_name="test",
            )

    def test_invalid_event_type_for_source(self):
        with pytest.raises(ValidationError, match="bug_bounty_submitted"):
            Event(
                source="gitlab",
                event_type="bug_bounty_submitted",  # blt-only type
                actor_id="1",
                actor_name="test",
            )

    def test_unknown_is_allowed_for_both_sources(self):
        e1 = Event(source="gitlab", event_type="unknown", actor_id="1", actor_name="x")
        e2 = Event(source="blt", event_type="unknown", actor_id="1", actor_name="x")
        assert e1.event_type == "unknown"
        assert e2.event_type == "unknown"

    def test_empty_actor_id_rejected(self):
        with pytest.raises(ValidationError, match="actor_id"):
            Event(
                source="gitlab",
                event_type="mr_opened",
                actor_id="",
                actor_name="test",
            )

    def test_empty_actor_name_rejected(self):
        with pytest.raises(ValidationError, match="actor_name"):
            Event(
                source="gitlab",
                event_type="mr_opened",
                actor_id="1",
                actor_name="",
            )

    def test_empty_event_type_rejected(self):
        with pytest.raises(ValidationError, match="event_type"):
            Event(
                source="gitlab",
                event_type="",
                actor_id="1",
                actor_name="test",
            )


class TestIdempotencyKey:
    """Idempotency key derivation."""

    def test_key_format(self):
        event = Event(
            source="gitlab",
            event_type="mr_opened",
            actor_id="12345",
            actor_name="test",
            timestamp=_utc("2026-07-15T10:22:00"),
        )
        assert event.idempotency_key == "gitlab:mr_opened:12345:2026-07-15T10:22:00Z"

    def test_key_changes_with_timestamp(self):
        e1 = Event(
            source="gitlab", event_type="mr_opened", actor_id="1", actor_name="x",
            timestamp=_utc("2026-07-15T10:22:00"),
        )
        e2 = Event(
            source="gitlab", event_type="mr_opened", actor_id="1", actor_name="x",
            timestamp=_utc("2026-07-15T10:23:00"),
        )
        assert e1.idempotency_key != e2.idempotency_key

    def test_key_changes_with_source(self):
        e1 = Event(
            source="gitlab", event_type="unknown", actor_id="1", actor_name="x",
            timestamp=_utc("2026-07-15T10:22:00"),
        )
        e2 = Event(
            source="blt", event_type="unknown", actor_id="1", actor_name="x",
            timestamp=_utc("2026-07-15T10:22:00"),
        )
        assert e1.idempotency_key != e2.idempotency_key


class TestTimezoneNormalization:
    """Timezone handling in the Event model."""

    def test_utc_timestamp_kept_naive(self):
        event = Event(
            source="gitlab",
            event_type="mr_opened",
            actor_id="1",
            actor_name="test",
            timestamp=_utc("2026-07-15T10:22:00"),
        )
        assert event.timestamp.tzinfo is None

    def test_offset_aware_converted_to_utc_naive(self):
        ts = datetime(2026, 7, 15, 12, 22, 0, tzinfo=timezone(timedelta(hours=2)))
        event = Event(
            source="gitlab",
            event_type="mr_opened",
            actor_id="1",
            actor_name="test",
            timestamp=ts,
        )
        assert event.timestamp == _utc("2026-07-15T10:22:00")
        assert event.timestamp.tzinfo is None

    def test_default_timestamp_is_utc_naive(self):
        event = Event(
            source="gitlab",
            event_type="mr_opened",
            actor_id="1",
            actor_name="test",
        )
        assert event.timestamp.tzinfo is None


class TestContributorAssignment:
    def test_with_contributor_returns_new_instance(self):
        import uuid
        event = Event(source="gitlab", event_type="mr_opened", actor_id="1", actor_name="x")
        cid = uuid.uuid4()
        updated = event.with_contributor(cid)
        assert event.contributor_id is None  # original unchanged
        assert updated.contributor_id == cid
        assert updated.id == event.id

    def test_all_gitlab_event_types_valid(self):
        valid_types = [
            "issue_opened", "mr_opened", "mr_merged",
            "review_requested", "pipeline_run", "note_added", "unknown",
        ]
        for t in valid_types:
            event = Event(source="gitlab", event_type=t, actor_id="1", actor_name="x")
            assert event.event_type == t

    def test_all_blt_event_types_valid(self):
        valid_types = [
            "bug_bounty_submitted", "bug_status_change",
            "hunt_activity", "unknown",
        ]
        for t in valid_types:
            event = Event(source="blt", event_type=t, actor_id="1", actor_name="x")
            assert event.event_type == t
