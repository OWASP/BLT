"""Regression tests for GitHub pull request review status."""

import pathlib
import sys
import unittest

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from utils import calculate_review_status


def review(login, state, submitted_at):
    return {
        "user": {"login": login},
        "state": state,
        "submitted_at": submitted_at,
    }


class CalculateReviewStatusTests(unittest.TestCase):
    def test_comment_after_approval_preserves_approval(self):
        reviews = [
            review("alice", "APPROVED", "2026-10-24T10:00:00Z"),
            review("alice", "COMMENTED", "2026-10-24T11:00:00Z"),
        ]
        self.assertEqual(calculate_review_status(reviews), "approved")

    def test_comment_after_changes_requested_preserves_request(self):
        reviews = [
            review("alice", "CHANGES_REQUESTED", "2026-10-24T10:00:00Z"),
            review("alice", "COMMENTED", "2026-10-24T11:00:00Z"),
        ]
        self.assertEqual(calculate_review_status(reviews), "changes_requested")

    def test_comment_does_not_erase_changes_requested_over_other_approval(self):
        reviews = [
            review("alice", "CHANGES_REQUESTED", "2026-10-24T10:00:00Z"),
            review("bob", "APPROVED", "2026-10-24T10:30:00Z"),
            review("alice", "COMMENTED", "2026-10-24T11:00:00Z"),
        ]
        self.assertEqual(calculate_review_status(reviews), "changes_requested")

    def test_dismissed_changes_request_is_cleared(self):
        reviews = [
            review("alice", "CHANGES_REQUESTED", "2026-10-24T10:00:00Z"),
            review("alice", "DISMISSED", "2026-10-24T11:00:00Z"),
        ]
        self.assertEqual(calculate_review_status(reviews), "pending")


if __name__ == "__main__":
    unittest.main()
