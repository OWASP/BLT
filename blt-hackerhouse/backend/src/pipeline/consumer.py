"""Queue consumer: process every enqueued event through the full pipeline.

Processing order: parse → deduplicate → persist → identity resolve
→ avatar state update → leaderboard score → DO broadcast → health record.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.dedup import is_duplicate
from identity.resolver import IdentityResolver, ResolutionResult
from models.event import Event
from models.room import AvatarState
from state.room_map import resolve_room
from broadcast.leaderboard import LeaderboardAccumulator
from broadcast.messages import build_avatar_move, build_identity_flag, build_leaderboard_update
from storage import (
    AvatarStateQueries,
    ContributorQueries,
    EventQueries,
    HealthStateQueries,
    utc_now_iso,
)


logger = logging.getLogger(__name__)


_accumulator = LeaderboardAccumulator()


async def process_pipeline_event(event_dict: dict[str, Any], db, env) -> bool:
    """Run the full pipeline for one event from the queue.

    Returns True on success.  Let exceptions propagate for queue retries.
    """
    # 1. Parse
    event = Event.model_validate(event_dict)

    # 2. Dedup
    if await is_duplicate(db, event):
        logger.debug("duplicate event skipped", extra={"idempotency_key": event.idempotency_key})
        return True

    # 3. Persist
    await EventQueries(db).insert(event)

    # 4. Identity resolution
    resolver = IdentityResolver(db)
    result: ResolutionResult = await resolver.resolve(event)

    # Update persisted event with resolved contributor_id
    await _update_event_contributor(db, str(event.id), str(result.contributor_id))
    event = event.with_contributor(result.contributor_id)

    # 5. Avatar state
    room_entry = resolve_room(event.event_type)
    avatar = AvatarState(
        contributor_id=result.contributor_id,
        floor=room_entry.floor,
        room=room_entry.room,
        last_event=event.event_type,
    )
    await AvatarStateQueries(db).upsert(avatar)

    # 6. Leaderboard score
    contributor_q = ContributorQueries(db)
    contributor = await contributor_q.get(result.contributor_id)
    if contributor is None:
        logger.warning(
            "contributor not found after resolution",
            extra={"contributor_id": str(result.contributor_id)},
        )
    else:
        delta = _accumulator.delta_for(event.event_type, event.metadata)
        if delta:
            contributor.add_score(delta)
            await contributor_q.upsert(contributor)

    # 7. Broadcast to DO
    try:
        do_stub = _get_do_stub(env)
        if do_stub is not None:
            broadcast_body = _build_broadcast_body(event, result, room_entry, contributor)
            await _broadcast_to_do(do_stub, broadcast_body)
    except Exception:
        logger.debug("broadcast skipped", exc_info=True)

    # 8. Health metrics
    health = HealthStateQueries(db)
    await health.upsert("queue_consumer", "last_processed_at", utc_now_iso())
    await health.upsert("queue_consumer", "last_event_type", event.event_type)

    logger.info(
        "pipeline event processed",
        extra={
            "event_type": event.event_type,
            "contributor_id": str(result.contributor_id),
            "identity_new": result.is_new,
        },
    )
    return True


def _build_broadcast_body(event, result, room_entry, contributor) -> dict[str, Any]:
    body: dict[str, Any] = {"type": "pipeline_update"}
    body["avatar_move"] = build_avatar_move(
        event, floor=room_entry.floor, room=room_entry.room
    ).model_dump(mode="json")

    if result.flag is not None:
        body["identity_flag"] = build_identity_flag(result.flag).model_dump(mode="json")

    if contributor is not None:
        delta = _accumulator.delta_for(event.event_type, event.metadata)
        if delta:
            body["leaderboard_update"] = build_leaderboard_update(
                result.contributor_id, contributor.score, delta, event.event_type,
            ).model_dump(mode="json")
    return body


def _get_do_stub(env) -> Any:
    try:
        do_id = env.WEBSOCKET_ROOM.idFromName("global-room")
        return env.WEBSOCKET_ROOM.get(do_id)
    except Exception:
        logger.debug("DO stub unavailable — skipping broadcast")
        return None


async def _broadcast_to_do(do_stub, body: dict[str, Any]) -> None:
    payload = json.dumps(body)
    try:
        import js as _js_bc  # noqa: F811
    except ImportError:
        logger.debug("js module unavailable — broadcast skipped")
        return
    js_req = _js_bc.Request.new(
        "http://do/internal/broadcast",
        {"method": "POST", "body": payload, "headers": {"Content-Type": "application/json"}},
    )
    await do_stub.fetch(js_req)


async def _update_event_contributor(db, event_id: str, contributor_id: str) -> None:
    await db.prepare(
        "UPDATE events SET contributor_id = ? WHERE id = ?"
    ).bind(contributor_id, event_id).run()
