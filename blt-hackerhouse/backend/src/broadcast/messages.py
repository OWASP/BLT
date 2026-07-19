"""Message builder helpers for the WebSocket hub."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from ..models.contributor import Contributor
from ..models.identity import IdentityFlag
from ..models.event import Event
from ..models.room import AvatarState
from ..models.websocket import (
    AvatarMoveMessage,
    IdentityFlagMessage,
    LeaderboardUpdateMessage,
    SnapshotContributor,
    SnapshotData,
    SnapshotMessage,
)

AVATAR_COUNT = 10


def avatar_url(contributor_id: UUID) -> str:
    """Deterministic avatar URL for a contributor based on their UUID.

    Hashes the UUID and picks one of the 10 available avatar PNGs.
    """
    digest = hashlib.sha256(str(contributor_id).encode()).hexdigest()
    idx = int(digest, 16) % AVATAR_COUNT
    return f"/avatars/avatar-{idx}.png"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc).replace(microsecond=0)


def build_snapshot(
    contributors: list[Contributor],
    avatars: dict[UUID, AvatarState],
    occupancy: dict[str, int],
) -> SnapshotMessage:
    entries = []
    for c in contributors:
        avatar = avatars.get(c.id)
        entries.append(
            SnapshotContributor(
                id=c.id,
                display_name=c.display_name,
                avatar_url=avatar_url(c.id),
                floor=avatar.floor if avatar else 1,
                room=avatar.room if avatar else "activity_monitor",
                identity_linked=c.is_linked,
                last_event=avatar.last_event if avatar else None,
                score=c.score,
            )
        )
    return SnapshotMessage(
        data=SnapshotData(
            contributors=entries,
            room_occupancy=occupancy,
            generated_at=_now(),
        )
    )


def build_avatar_move(event: Event, floor: int, room: str) -> AvatarMoveMessage:
    contributor_id = event.contributor_id or UUID(int=0)
    return AvatarMoveMessage(
        contributor_id=contributor_id,
        floor=floor,
        room=room,
        event_type=event.event_type,
        timestamp=_now(),
    )


def build_identity_flag(flag: IdentityFlag) -> IdentityFlagMessage:
    return IdentityFlagMessage(
        suggested_link=flag.model_dump()["suggested_link"]
        if hasattr(flag.model_dump()["suggested_link"], "model_dump")
        else flag.model_dump()["suggested_link"],
        contributor_id=flag.contributor_id,
    )


def build_leaderboard_update(
    contributor_id: UUID,
    score: int,
    delta: int,
    last_event: str,
) -> LeaderboardUpdateMessage:
    return LeaderboardUpdateMessage(
        contributor_id=contributor_id,
        score=score,
        delta=delta,
        last_event=last_event,
    )


def serialize(message: BaseModel | Any) -> str:
    """JSON-encode a message using the model's Pydantic dump."""
    if hasattr(message, "model_dump_json"):
        return message.model_dump_json()
    if isinstance(message, dict):
        import json
        return json.dumps(message, default=str)
    raise TypeError(f"Cannot serialize message of type {type(message)!r}")