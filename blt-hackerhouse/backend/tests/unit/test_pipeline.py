"""Pipeline consumer tests."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.models.contributor import Contributor
from src.models.event import Event
from src.models.room import AvatarState
from src.pipeline.consumer import process_pipeline_event
from src.storage import AvatarStateQueries, ContributorQueries, EventQueries


@pytest.mark.asyncio
async def test_process_event_full_pipeline(db):
    """End-to-end: event is persisted, contributor created, avatar updated, health recorded."""
    from src.storage import HealthStateQueries

    event = Event(source="gitlab", event_type="mr_merged", actor_id="99", actor_name="bob", repository="org/repo")
    event_dict = event.model_dump(mode="json")

    # Use a mock env that will fail-safe on DO stub lookup
    mock_env = MagicMock()

    result = await process_pipeline_event(event_dict, db, mock_env)
    assert result is True

    # Verify persistence
    eq = EventQueries(db)
    assert await eq.count() == 1

    # Verify contributor created
    cq = ContributorQueries(db)
    contributors = await cq.list_all()
    assert len(contributors) == 1
    contributor = contributors[0]
    assert contributor.display_name == "bob"
    assert contributor.score == 10  # mr_merged = 10 points

    # Verify avatar state updated
    aq = AvatarStateQueries(db)
    avatar = await aq.get(contributor.id)
    assert avatar is not None
    assert avatar.floor == 3  # release_management_room
    assert avatar.room == "release_management_room"
    assert avatar.last_event == "mr_merged"

    # Verify health recorded
    hq = HealthStateQueries(db)
    last_event = await hq.get("queue_consumer", "last_event_type")
    assert last_event == "mr_merged"
    last_processed = await hq.get("queue_consumer", "last_processed_at")
    assert last_processed is not None


@pytest.mark.asyncio
async def test_duplicate_event_is_skipped(db):
    """Duplicate events are deduped and not re-processed."""
    event = Event(source="gitlab", event_type="note_added", actor_id="55", actor_name="charlie")
    event_dict = event.model_dump(mode="json")
    mock_env = MagicMock()

    # First time should succeed
    r1 = await process_pipeline_event(event_dict, db, mock_env)
    assert r1 is True
    assert await EventQueries(db).count() == 1

    # Second time should skip (same idempotency key)
    r2 = await process_pipeline_event(event_dict, db, mock_env)
    assert r2 is True
    assert await EventQueries(db).count() == 1


@pytest.mark.asyncio
async def test_event_with_zero_score(db):
    """Events with 0-point event_type still create contributor and avatar."""
    event = Event(source="gitlab", event_type="pipeline_run", actor_id="66", actor_name="dave",
                  metadata={"status": "failed"})
    event_dict = event.model_dump(mode="json")
    mock_env = MagicMock()

    result = await process_pipeline_event(event_dict, db, mock_env)
    assert result is True

    cq = ContributorQueries(db)
    contributors = await cq.list_all()
    assert len(contributors) == 1
    assert contributors[0].score == 0  # failed pipeline = 0 points


@pytest.mark.asyncio
async def test_unknown_event_type_routes_to_default_room(db):
    """Unmapped event types fall back to the activity_monitor room."""
    event = Event(source="gitlab", event_type="unknown", actor_id="77", actor_name="eve")
    event_dict = event.model_dump(mode="json")
    mock_env = MagicMock()

    result = await process_pipeline_event(event_dict, db, mock_env)
    assert result is True

    cq = ContributorQueries(db)
    contributors = await cq.list_all()
    c = contributors[0]

    aq = AvatarStateQueries(db)
    avatar = await aq.get(c.id)
    assert avatar is not None
    assert avatar.floor == 1
    assert avatar.room == "activity_monitor"


@pytest.mark.asyncio
async def test_existing_contributor_score_accumulates(db):
    """Events for the same contributor accumulate score."""
    c = Contributor(id=uuid4(), display_name="frank", usernames=["frank"],
                    platform_ids={"gitlab_id": "88"}, is_linked=True, score=5)
    await ContributorQueries(db).upsert(c)

    # Insert identity mapping so resolution finds the existing contributor
    from src.storage import IdentityQueries
    from src.models.identity import IdentityMapping
    await IdentityQueries(db).insert(
        IdentityMapping(platform="gitlab", platform_user_id="88",
                        contributor_id=c.id, confidence=1.0)
    )

    event = Event(source="gitlab", event_type="mr_merged", actor_id="88", actor_name="frank")
    event_dict = event.model_dump(mode="json")
    mock_env = MagicMock()

    result = await process_pipeline_event(event_dict, db, mock_env)
    assert result is True

    loaded = await ContributorQueries(db).get(c.id)
    assert loaded is not None
    assert loaded.score == 15  # 5 + 10 for mr_merged
