"""Identity resolution pipeline tests (4 stages)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.identity.resolver import IdentityResolver
from src.models.contributor import Contributor
from src.models.event import Event
from src.models.identity import IdentityMapping
from src.storage import ContributorQueries, IdentityQueries


@pytest.mark.asyncio
async def test_stage1_exact_match(db):
    cid = uuid4()
    contrib = Contributor(
        id=cid,
        display_name="Alice",
        usernames=["alice"],
        aliases=["Alice"],
        platform_ids={"gitlab_id": "42"},
        is_linked=True,
    )
    await ContributorQueries(db).upsert(contrib)
    await IdentityQueries(db).insert(
        IdentityMapping(
            platform="gitlab",
            platform_user_id="42",
            contributor_id=cid,
            confidence=1.0,
        )
    )

    event = Event(source="gitlab", event_type="note_added", actor_id="42", actor_name="alice")
    result = await IdentityResolver(db).resolve(event)
    assert result.contributor_id == cid
    assert result.confidence == 1.0
    assert result.is_new is False


@pytest.mark.asyncio
async def test_stage2_levenshtein_match(db):
    cid = uuid4()
    contrib = Contributor(
        id=cid,
        display_name="Bob Smith",
        usernames=["bobsmith"],
        aliases=[],
        platform_ids={"gitlab_id": "1"},
        is_linked=False,
    )
    cq = ContributorQueries(db)
    await cq.upsert(contrib)

    # "bobsmyth" is Levenshtein distance 1 from "bobsmith"
    event = Event(source="gitlab", event_type="note_added", actor_id="999", actor_name="bobsmyth")
    result = await IdentityResolver(db).resolve(event)
    assert result.contributor_id == cid
    assert result.confidence == 0.75
    assert result.is_new is False
    assert result.flag is not None


@pytest.mark.asyncio
async def test_stage4_unlinked_fallback(db):
    event = Event(source="blt", event_type="bug_bounty_submitted", actor_id="777", actor_name="newhunter")
    result = await IdentityResolver(db).resolve(event)
    assert result.is_new is True
    assert result.confidence == 0.0
    loaded = await ContributorQueries(db).get(result.contributor_id)
    assert loaded is not None
    assert loaded.display_name == "newhunter"
    assert loaded.platform_ids["blt_id"] == "777"