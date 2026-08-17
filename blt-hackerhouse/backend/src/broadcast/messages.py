"""Message builder helpers for the WebSocket hub."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from models.contributor import Contributor
from models.event import Event
from models.identity import IdentityFlag
from models.websocket import (
    AvatarMoveMessage,
    IdentityFlagLink,
    IdentityFlagMessage,
    IdentityFlagSource,
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
    avatars: dict[str, dict],
    occupancy: dict[str, int],
) -> SnapshotMessage:
    entries = []
    for c in contributors:
        avatar = avatars.get(str(c.id))
        entries.append(
            SnapshotContributor(
                id=c.id,
                display_name=c.display_name,
                avatar_url=avatar_url(c.id),
                floor=avatar["floor"] if avatar else 1,
                room=avatar["room"] if avatar else "activity_monitor",
                identity_linked=c.is_linked,
                last_event=avatar["last_event"] if avatar else None,
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


def build_avatar_move(event: Event, floor: int, room: str, *, contributor_id: UUID) -> AvatarMoveMessage:
    return AvatarMoveMessage(
        contributor_id=contributor_id,
        floor=floor,
        room=room,
        event_type=event.event_type,
        timestamp=_now(),
    )


def build_identity_flag(flag: IdentityFlag) -> IdentityFlagMessage:
    return IdentityFlagMessage(
        suggested_link=IdentityFlagLink(
            source_a=IdentityFlagSource(
                platform=flag.source_a.platform,
                username=flag.source_a.username,
                user_id=flag.source_a.user_id,
            ),
            source_b=IdentityFlagSource(
                platform=flag.source_b.platform,
                username=flag.source_b.username,
                user_id=flag.source_b.user_id,
            ),
            confidence=flag.confidence,
        ),
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
