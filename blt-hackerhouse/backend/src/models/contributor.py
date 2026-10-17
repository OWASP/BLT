"""
Unified contributor identity models.

One ``Contributor`` represents a real-world person regardless of how
many platforms (GitLab, BLT) they appear on.  The identity resolution
pipeline produces and updates these records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Contributor(BaseModel):
    """A unified contributor identity.

    JSON columns (``usernames``, ``aliases``, ``platform_ids``) are
    stored as text in SQLite and deserialized by application code.
    The Pydantic model validates them as native Python structures.
    """

    id: UUID = Field(default_factory=uuid4, description="UUID v4 primary key.")

    display_name: str = Field(
        description="Primary display name shown in the house UI.",
        min_length=1,
    )

    usernames: list[str] = Field(
        default_factory=list,
        description="Lowercase usernames collected across all platforms. Used by Stage 2 identity resolution (Levenshtein).",
    )

    aliases: list[str] = Field(
        default_factory=list,
        description="Display name variations. Used by Stage 3 identity resolution (Jaccard).",
    )

    platform_ids: dict[str, str] = Field(
        default_factory=dict,
        description="Platform → native user ID mapping. e.g. {'gitlab_id': '12345', 'blt_id': '678'}.",
    )

    is_linked: bool = Field(
        default=False,
        description="True when identity is confirmed across at least two platforms.",
    )

    score: int = Field(
        default=0,
        ge=0,
        description="Accumulated contributor score for the leaderboard.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).replace(microsecond=0),
        description="UTC timestamp of identity creation.",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).replace(microsecond=0),
        description="UTC timestamp of last update.",
    )

    def add_username(self, username: str) -> None:
        """Append a lowercase username if not already present."""
        lower = username.lower().strip()
        if lower and lower not in self.usernames:
            self.usernames.append(lower)
            self.updated_at = datetime.now(tz=timezone.utc).replace(microsecond=0)

    def add_alias(self, alias: str) -> None:
        """Append a display name alias if not already present."""
        alias = alias.strip()
        if alias and alias not in self.aliases:
            self.aliases.append(alias)
            self.updated_at = datetime.now(tz=timezone.utc).replace(microsecond=0)

    def add_platform_id(self, platform: str, platform_id: str) -> None:
        """Record a platform-specific user ID."""
        key = f"{platform}_id"
        self.platform_ids[key] = str(platform_id)
        if len(self.platform_ids) >= 2:
            self.is_linked = True
        self.updated_at = datetime.now(tz=timezone.utc).replace(microsecond=0)

    def add_score(self, points: int) -> None:
        """Increment score by a positive amount."""
        if points < 0:
            raise ValueError("Score increment must be non-negative")
        self.score += points
        self.updated_at = datetime.now(tz=timezone.utc).replace(microsecond=0)


class ContributorSnapshot(BaseModel):
    """Lightweight view of a contributor for WebSocket snapshots.

    Does not include internal fields like ``usernames`` or ``aliases``
    — only what the frontend needs to render an avatar.
    """

    id: UUID
    display_name: str
    floor: int | None = Field(default=None, ge=1, le=3)
    room: str | None = None
    identity_linked: bool = False
    last_event: str | None = None
    score: int = 0

    @classmethod
    def from_contributor(
        cls,
        contributor: Contributor,
        floor: int | None = None,
        room: str | None = None,
        last_event: str | None = None,
    ) -> "ContributorSnapshot":
        """Build a snapshot from a Contributor and optional avatar state."""
        return cls(
            id=contributor.id,
            display_name=contributor.display_name,
            floor=floor,
            room=room,
            identity_linked=contributor.is_linked,
            last_event=last_event,
            score=contributor.score,
        )
