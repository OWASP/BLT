"""Leaderboard scoring rules + accumulator (VF16)."""

from __future__ import annotations

from typing import Final


# Per MVP_V1_SPEC.md §VF16 — explicit per-event-type scoring.
SCORING_RULES: Final[dict[str, int]] = {
    "mr_merged":            10,
    "bug_bounty_submitted": 15,
    "review_requested":      5,
    "hunt_activity":         5,
    "issue_opened":          3,
    "mr_opened":             2,
    "pipeline_run":          2,   # success only — caller filters
    "note_added":            1,
    # Zero-point (omitted): pipeline_run (failed), unknown, duplicates
}


class LeaderboardAccumulator:
    """Compute score deltas from a normalized event."""

    def __init__(self) -> None:
        self._totals: dict[str, int] = {}

    def delta_for(self, event_type: str, metadata: dict) -> int:
        """Return the score change for an event type (0 if unscored)."""
        if event_type == "pipeline_run":
            # Only successful pipelines earn points.
            if (metadata.get("status") or "").lower() != "success":
                return 0
        return SCORING_RULES.get(event_type, 0)

    def record(self, contributor_id: str, event_type: str, metadata: dict) -> int:
        """Record a delta locally for fast leaderboard reads."""
        delta = self.delta_for(event_type, metadata)
        if delta:
            self._totals[contributor_id] = self._totals.get(contributor_id, 0) + delta
        return delta

    def snapshot(self) -> dict[str, int]:
        return dict(self._totals)

    def reset(self) -> None:
        self._totals.clear()