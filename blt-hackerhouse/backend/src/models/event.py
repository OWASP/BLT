"""
Canonical internal event data transfer object.

Every source-specific payload is normalized into an ``Event`` before
any downstream processing.  The ``Event`` is the only data structure
that the state reducer, broadcast hub, and storage layer operate on.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field, model_validator


def _utc_now() -> datetime:
    """Return the current time in UTC with second precision."""
    return datetime.now(tz=timezone.utc).replace(microsecond=0)


class Event(BaseModel):
    """A single normalized contributor activity event.

    This is the single internal representation that every downstream
    component consumes.  Source-specific adapters are responsible for
    producing ``Event`` instances from raw platform payloads.

    Identity resolution runs *after* normalization — the
    ``contributor_id`` field is populated as a separate step.
    """

    id: UUID = Field(default_factory=uuid4, description="UUID v4 generated at normalization time.")

    source: Literal["gitlab", "blt"] = Field(
        description="Platform that produced this event.",
    )

    event_type: str = Field(
        description=(
            "Internal event type: issue_opened, mr_opened, mr_merged, "
            "review_requested, pipeline_run, note_added, "
            "bug_bounty_submitted, bug_status_change, hunt_activity, or unknown."
        ),
        min_length=1,
    )

    actor_id: str = Field(
        description="Platform-native user identifier (GitLab user.id or BLT user.id).",
        min_length=1,
    )

    actor_name: str = Field(
        description="Human-readable name for avatar label (GitLab user.username or BLT user.username).",
        min_length=1,
    )

    repository: str = Field(
        default="",
        description="Project path (GitLab project.path_with_namespace) or repo extracted from BLT hunt data.",
    )

    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp parsed from the source event (when it happened, not when we ingested it).",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific fields preserved for the activity feed and overlay (title, url, branch, etc.).",
    )

    contributor_id: UUID | None = Field(
        default=None,
        description="Resolved unified contributor identity. Set after identity resolution completes.",
    )

    sequence_number: int | None = Field(
        default=None,
        description="Monotonic sequence number assigned by storage at insert time. Used for out-of-order detection.",
    )

    @computed_field(description="Idempotency key for deduplication.")
    @property
    def idempotency_key(self) -> str:
        """Derived key: ``source:event_type:actor_id:timestamp``."""
        ts = self.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"{self.source}:{self.event_type}:{self.actor_id}:{ts}"

    @model_validator(mode="after")
    def _ensure_utc_timestamp(self) -> "Event":
        """Strip timezone info if present and normalize to UTC.

        Pydantic parses ISO 8601 strings with offsets; we store
        everything as a naive datetime assumed to be UTC for SQLite
        compatibility.
        """
        if self.timestamp.tzinfo is not None:
            self.timestamp = self.timestamp.astimezone(timezone.utc).replace(tzinfo=None)
        return self

    @model_validator(mode="after")
    def _validate_event_type(self) -> "Event":
        """Ensure event_type matches source capabilities."""
        valid = {
            "gitlab": {
                "issue_opened", "mr_opened", "mr_merged",
                "review_requested", "pipeline_run", "note_added", "unknown",
            },
            "blt": {
                "bug_bounty_submitted", "bug_status_change",
                "hunt_activity", "unknown",
            },
        }
        allowed = valid.get(self.source, set())
        if self.event_type not in allowed:
            raise ValueError(
                f"event_type '{self.event_type}' is not valid for source '{self.source}'. "
                f"Allowed: {sorted(allowed)}"
            )
        return self

    def with_contributor(self, contributor_id: UUID) -> "Event":
        """Return a copy of this event with ``contributor_id`` set."""
        return self.model_copy(update={"contributor_id": contributor_id})
