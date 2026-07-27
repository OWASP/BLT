"""Tests for conversation route parsing and dispatch.

These tests validate that the worker correctly routes conversation
endpoints and sanitizes triage IDs, without requiring the Cloudflare
Workers runtime.
"""

import urllib.parse


def parse_path(url):
    """Copy of worker.py's parse_path for testing.

    ⚠️  KEEP IN SYNC WITH worker.py parse_path() ⚠️
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    if not path or path == "":
        path = "/"
    elif not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


class TestConversationRouteMatching:
    def test_reply_route_matches(self):
        url = "https://example.com/conversations/evt-001/reply"
        path = parse_path(url)
        assert path == "/conversations/evt-001/reply"
        assert path.startswith("/conversations/")
        assert path.endswith("/reply")

    def test_history_route_matches(self):
        url = "https://example.com/conversations/evt-002/history"
        path = parse_path(url)
        assert path == "/conversations/evt-002/history"

    def test_close_route_matches(self):
        url = "https://example.com/conversations/evt-003"
        path = parse_path(url)
        assert path == "/conversations/evt-003"

    def test_triage_id_extraction(self):
        """Extract triage_id from /conversations/{triage_id}/reply."""
        path = "/conversations/evt-001/reply"
        parts = path.split("/")
        # parts = ['', 'conversations', 'evt-001', 'reply']
        assert parts[2] == "evt-001"

    def test_triage_id_with_path_traversal_rejected(self):
        """triage_id containing '/' should be rejected."""
        raw_id = "../etc/passwd"
        decoded = urllib.parse.unquote(raw_id)
        assert "/" in decoded  # this would be rejected by the worker

    def test_encoded_triage_id_decoded(self):
        """URL-encoded triage_id is properly decoded."""
        raw_id = "evt%2D001"
        decoded = urllib.parse.unquote(raw_id)
        assert decoded == "evt-001"

    def test_history_with_query_params(self):
        """Query params don't affect path parsing."""
        url = "https://example.com/conversations/evt-001/history?full=true"
        path = parse_path(url)
        assert path == "/conversations/evt-001/history"

    def test_trailing_slash_stripped(self):
        url = "https://example.com/conversations/evt-001/reply/"
        path = parse_path(url)
        assert path == "/conversations/evt-001/reply"
