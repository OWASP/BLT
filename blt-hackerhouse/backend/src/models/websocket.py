"""
WebSocket message type contracts.

All server → client communication uses these typed message formats.
The message contract is locked — the frontend integration has no
discovery phase.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SnapshotMessage(BaseModel):
    """Full state snapshot sent to every newly connected client."""

    type: Literal["snapshot"] = "snapshot"

    data: SnapshotData = Field(
        description="Complete current state: contributors, room occupancy, and generation timestamp.",
    )


class SnapshotData(BaseModel):
    """Payload for the snapshot message."""

    contributors: list[SnapshotContributor] = Field(
        default_factory=list,
        description="All contributors with their current positions.",
    )

    room_occupancy: dict[str, int] = Field(
        default_factory=dict,
        description="Room identifier → number of contributors currently in that room.",
    )

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).replace(microsecond=0),
        description="UTC timestamp when this snapshot was generated.",
    )


class SnapshotContributor(BaseModel):
    """A single contributor entry in the snapshot."""

    id: UUID
    display_name: str
    floor: int
    room: str
    identity_linked: bool
    last_event: str | None = None
    score: int = 0


class AvatarMoveMessage(BaseModel):
    """Sent on every avatar position change."""

    type: Literal["avatar_move"] = "avatar_move"

    contributor_id: UUID = Field(description="The contributor who moved.")

    floor: int = Field(ge=1, le=3)

    room: str = Field(min_length=1)

    event_type: str = Field(min_length=1, description="The event that caused this move.")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).replace(microsecond=0),
    )


class IdentityFlagMessage(BaseModel):
    """Sent when the resolver finds a fuzzy match needing maintainer confirmation."""

    type: Literal["identity_flag"] = "identity_flag"

    suggested_link: IdentityFlagLink = Field(
        description="The two platform identities and the confidence of the match.",
    )

    contributor_id: UUID = Field(
        description="The contributor being linked.",
    )


class IdentityFlagLink(BaseModel):
    """Two platform identities that may belong to the same contributor."""

    source_a: IdentityFlagSource
    source_b: IdentityFlagSource
    confidence: float = Field(ge=0.0, le=1.0)


class IdentityFlagSource(BaseModel):
    """A single platform identity reference in an identity flag."""

    platform: Literal["gitlab", "blt"]
    username: str | None = None
    user_id: str | None = None


class LeaderboardUpdateMessage(BaseModel):
    """Sent when a contributor's score changes."""

    type: Literal["leaderboard_update"] = "leaderboard_update"

    contributor_id: UUID

    score: int = Field(ge=0, description="New total score.")

    delta: int = Field(description="Score change (positive).")

    last_event: str = Field(min_length=1, description="The event that caused this score change.")
