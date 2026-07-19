"""
Identity mapping and identity flag models.

Maps platform-specific user IDs to unified contributors and surfaces
fuzzy matches for maintainer confirmation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


Platform = Literal["gitlab", "blt"]


class IdentityMapping(BaseModel):
    """Maps a single platform identity to a unified contributor.

    One row per platform per person.  The UNIQUE constraint on
    ``(platform, platform_user_id)`` enables O(1) exact-match lookups
    during Stage 1 identity resolution.
    """

    id: int | None = Field(
        default=None,
        description="Auto-increment primary key. None until persisted.",
    )

    platform: Platform = Field(
        description="Platform this mapping represents: 'gitlab' or 'blt'.",
    )

    platform_user_id: str = Field(
        description="The platform's native user identifier.",
        min_length=1,
    )

    contributor_id: UUID = Field(
        description="FK to the unified contributor record.",
    )

    confidence: float = Field(
        description=(
            "Resolution confidence: 1.0 = exact, 0.75 = Levenshtein, "
            "0.60 = Jaccard, 0.0 = unlinked."
        ),
        ge=0.0,
        le=1.0,
    )

    confirmed_by: str | None = Field(
        default=None,
        description="Set when a maintainer confirms or rejects this mapping via the overlay UI.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).replace(microsecond=0),
        description="UTC timestamp of mapping creation.",
    )


class IdentityFlag(BaseModel):
    """A suggested identity link that requires maintainer confirmation.

    Sent as a WebSocket ``identity_flag`` message when the resolver
    finds a fuzzy match (Stages 2-3).
    """

    source_a: PlatformIdentity = Field(
        description="First platform identity in the suggested link.",
    )

    source_b: PlatformIdentity = Field(
        description="Second platform identity in the suggested link.",
    )

    confidence: float = Field(
        description="Confidence score of the suggested match.",
        ge=0.0,
        le=1.0,
    )

    contributor_id: UUID = Field(
        description="The contributor these identities are being linked to.",
    )


class PlatformIdentity(BaseModel):
    """A single platform identity reference used in IdentityFlag."""

    platform: Platform = Field(
        description="'gitlab' or 'blt'.",
    )

    username: str | None = Field(
        default=None,
        description="Display name or username on this platform.",
    )

    user_id: str | None = Field(
        default=None,
        description="Platform-native user ID.",
    )
