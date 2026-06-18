"""Leaderboard scoring rules tests."""

from __future__ import annotations

from src.broadcast.leaderboard import SCORING_RULES, LeaderboardAccumulator


def test_scoring_table_matches_spec():
    # From MVP_V1_SPEC.md §VF16
    assert SCORING_RULES["mr_merged"] == 10
    assert SCORING_RULES["bug_bounty_submitted"] == 15
    assert SCORING_RULES["review_requested"] == 5
    assert SCORING_RULES["hunt_activity"] == 5
    assert SCORING_RULES["issue_opened"] == 3
    assert SCORING_RULES["mr_opened"] == 2
    assert SCORING_RULES["pipeline_run"] == 2
    assert SCORING_RULES["note_added"] == 1


def test_pipeline_failed_awards_zero():
    acc = LeaderboardAccumulator()
    assert acc.delta_for("pipeline_run", {"status": "failed"}) == 0
    assert acc.delta_for("pipeline_run", {"status": "running"}) == 0
    assert acc.delta_for("pipeline_run", {"status": "success"}) == 2


def test_unknown_awards_zero():
    acc = LeaderboardAccumulator()
    assert acc.delta_for("unknown", {}) == 0


def test_record_accumulates():
    acc = LeaderboardAccumulator()
    assert acc.record("c1", "mr_merged", {}) == 10
    assert acc.record("c1", "issue_opened", {}) == 3
    assert acc.snapshot() == {"c1": 13}