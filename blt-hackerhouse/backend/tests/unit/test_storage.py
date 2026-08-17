"""Storage layer tests: events, contributors, identity mappings, DLQ."""

from __future__ import annotations

import pytest
from uuid import uuid4

from src.models.contributor import Contributor
from src.models.event import Event
from src.models.identity import IdentityMapping
from src.models.room import AvatarState
from src.storage import (
    AvatarStateQueries,
    ContributorQueries,
    DeadLetterQueries,
    EventQueries,
    IdentityQueries,
)


@pytest.mark.asyncio
async def test_event_insert_is_idempotent(db):
    q = EventQueries(db)
    event = Event(
        source="gitlab",
        event_type="mr_opened",
        actor_id="42",
        actor_name="alice",
        repository="OWASP-BLT/BLT",
    )
    assert await q.insert(event) is True
    # Same key inserted again → ignored.
    assert await q.insert(event) is False
    assert await q.count() == 1


@pytest.mark.asyncio
async def test_event_sequence_assignment(db):
    q = EventQueries(db)
    event = Event(source="gitlab", event_type="note_added", actor_id="1", actor_name="x")
    await q.insert(event)
    await q.assign_sequence(event.id, 1)
    loaded = await q.get_by_idempotency_key(event.idempotency_key)
    assert loaded is not None
    assert loaded.sequence_number == 1


@pytest.mark.asyncio
async def test_contributor_upsert_roundtrip(db):
    q = ContributorQueries(db)
    c = Contributor(
        id=uuid4(),
        display_name="Alice Example",
        usernames=["alice"],
        aliases=["Alice Example"],
        platform_ids={"gitlab_id": "42"},
        is_linked=False,
        score=7,
    )
    await q.upsert(c)
    loaded = await q.get(c.id)
    assert loaded is not None
    assert loaded.display_name == "Alice Example"
    assert loaded.usernames == ["alice"]
    assert loaded.score == 7

    # Mutate and upsert again
    loaded.add_score(3)
    await q.upsert(loaded)
    again = await q.get(c.id)
    assert again is not None
    assert again.score == 10


@pytest.mark.asyncio
async def test_avatar_state_upsert(db):
    from src.models.contributor import Contributor
    cid = uuid4()
    await ContributorQueries(db).upsert(
        Contributor(id=cid, display_name="A", usernames=["a"], platform_ids={"gitlab_id": "1"})
    )
    q = AvatarStateQueries(db)
    state = AvatarState(contributor_id=cid, floor=2, room="merge_request_room", last_event="mr_opened")
    await q.upsert(state)

    # Move contributor
    state.room = "code_review_room"
    state.floor = 3
    state.last_event = "review_requested"
    await q.upsert(state)

    loaded = await q.get(cid)
    assert loaded is not None
    assert loaded.room == "code_review_room"
    assert loaded.floor == 3


@pytest.mark.asyncio
async def test_occupancy_aggregation(db):
    from src.models.contributor import Contributor
    cq = ContributorQueries(db)
    q = AvatarStateQueries(db)
    for cid, room, floor in [
        (uuid4(), "merge_request_room", 2),
        (uuid4(), "merge_request_room", 2),
        (uuid4(), "code_review_room", 3),
    ]:
        await cq.upsert(
            Contributor(
                id=cid,
                display_name=str(cid),
                usernames=[str(cid)],
                platform_ids={"gitlab_id": str(cid)},
            )
        )
        await q.upsert(
            AvatarState(contributor_id=cid, floor=floor, room=room, last_event="mr_opened")
        )

    occupancy = await q.occupancy()
    assert occupancy["merge_request_room"] == 2
    assert occupancy["code_review_room"] == 1


@pytest.mark.asyncio
async def test_identity_mapping_unique(db):
    from src.models.contributor import Contributor
    cq = ContributorQueries(db)
    cid = uuid4()
    await cq.upsert(
        Contributor(id=cid, display_name="x", usernames=["x"], platform_ids={"gitlab_id": "42"})
    )
    q = IdentityQueries(db)
    m1 = IdentityMapping(platform="gitlab", platform_user_id="42", contributor_id=cid, confidence=1.0)
    await q.insert(m1)

    # Inserting a different mapping with the same (platform, user_id) updates.
    m2 = IdentityMapping(platform="gitlab", platform_user_id="42", contributor_id=cid, confidence=0.75)
    await q.insert(m2)
    found = await q.lookup("gitlab", "42")
    assert found is not None
    assert found.confidence == 0.75


@pytest.mark.asyncio
async def test_dead_letter_cap_at_500(db):
    q = DeadLetterQueries(db)
    # Insert exactly the cap; should not evict.
    for i in range(DeadLetterQueries.CAP):
        await q.add(event_id=None, source="blt", error=f"err{i}", payload={"i": i})
    rows = await q.list_recent(limit=10_000)
    assert len(rows) == DeadLetterQueries.CAP

    # Inserting one more should evict exactly one.
    await q.add(event_id=None, source="blt", error="overflow", payload={})
    rows = await q.list_recent(limit=10_000)
    assert len(rows) == DeadLetterQueries.CAP
    # The overflow message should be present (oldest entry evicted).
    errors = {r["error"] for r in rows}
    assert "overflow" in errors


@pytest.mark.asyncio
async def test_cursor_upsert(db):
    from src.storage import CursorQueries
    q = CursorQueries(db)
    assert await q.get("blt_bugs") is None
    await q.upsert("blt_bugs", 123)
    loaded = await q.get("blt_bugs")
    assert loaded is not None
    assert loaded[0] == 123
    await q.upsert("blt_bugs", 456)
    loaded = await q.get("blt_bugs")
    assert loaded is not None
    assert loaded[0] == 456


@pytest.mark.asyncio
async def test_health_state_upsert_and_get(db):
    from src.storage import HealthStateQueries, utc_now_iso

    q = HealthStateQueries(db)

    await q.upsert("queue_consumer", "last_processed_at", "2026-07-21T10:00:00+00:00")
    val = await q.get("queue_consumer", "last_processed_at")
    assert val == "2026-07-21T10:00:00+00:00"

    # Upsert overwrites
    await q.upsert("queue_consumer", "last_processed_at", "2026-07-21T11:00:00+00:00")
    val2 = await q.get("queue_consumer", "last_processed_at")
    assert val2 == "2026-07-21T11:00:00+00:00"

    # Non-existent field returns None
    assert await q.get("queue_consumer", "nonexistent") is None
    assert await q.get("nonexistent_component", "any") is None

    # get_component returns all fields for a component
    await q.upsert("queue_consumer", "last_event_type", "mr_opened")
    comp = await q.get_component("queue_consumer")
    assert "last_processed_at" in comp
    assert "last_event_type" in comp