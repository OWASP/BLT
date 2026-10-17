"""
Room routing and avatar state models.

Defines the three-floor house layout, room occupancy tracking,
and per-contributor position state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RoomMapEntry(BaseModel):
    """A single entry in the room routing map."""

    floor: int = Field(ge=1, le=3, description="Floor number: 1 (Ops), 2 (Dev), 3 (Review).")
    room: str = Field(min_length=1, description="Room identifier matching house layout.")


class AvatarState(BaseModel):
    """Current position of a single contributor in the house.

    Uses ``INSERT OR REPLACE`` semantics — one row per contributor,
    always reflecting their most recent position.
    """

    contributor_id: UUID = Field(description="FK to the unified contributor record (also PK).")

    floor: int = Field(ge=1, le=3)

    room: str = Field(min_length=1)

    last_event: str = Field(
        min_length=1,
        description="Most recent event_type that moved this contributor.",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).replace(microsecond=0),
        description="UTC timestamp of last position update.",
    )


class RoomOccupancy(BaseModel):
    """Aggregated count of contributors per room.

    Built by ``SELECT room, COUNT(*) FROM avatar_state GROUP BY room``.
    """

    occupancy: dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of room identifier → number of contributors currently in that room.",
    )

    @classmethod
    def from_avatar_states(cls, states: list[AvatarState]) -> "RoomOccupancy":
        """Compute occupancy from a list of current avatar states."""
        counts: dict[str, int] = {}
        for state in states:
            counts[state.room] = counts.get(state.room, 0) + 1
        return cls(occupancy=counts)
