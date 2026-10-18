import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger  # noqa: E402


class FakeClient:
    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def get(self, operation, params=()):
        self.calls.append((operation, dict(params)))
        return self.answers(operation, dict(params))

    def tree(self, path, ref=""):
        return self.get("tree", [("path", path)] + ([("ref", ref)] if ref else []))

    def blobs(self, paths, ref=""):
        return {p: self.get("blob", [("path", p)]) for p in paths}


ISSUE = {
    "number": 3, "title": "[blt-pages] Broken link", "status": "closed", "labels": ["bug"],
    "events": [
        {"type": "open", "id": "o1", "ts": 1, "body": "first"},
        {"type": "edit", "id": "e1", "target": "o1", "ts": 2, "body": "edited"},
        {"type": "comment", "id": "c1", "ts": 3, "authorName": "ann", "body": "hi"},
        {"type": "comment", "id": "c2", "ts": 4, "authorName": "bob", "body": "gone"},
        {"type": "delete", "id": "d1", "target": "c2", "ts": 5},
        {"type": "vote", "id": "v1", "ts": 6, "authorName": "ann"},
        {"type": "vote", "id": "v2", "ts": 7, "authorName": "ann"},
        {"type": "status", "id": "s1", "ts": 1792290689619, "status": "closed"},
    ],
}


class LedgerTest(unittest.TestCase):
    def test_issue_helpers(self):
        self.assertEqual(ledger.body(ISSUE), "edited")
        self.assertEqual([c["id"] for c in ledger.comments(ISSUE)], ["c1"])
        self.assertEqual(ledger.voters(ISSUE), ["ann"])
        self.assertEqual(ledger.issue_projects(ISSUE), ["blt-pages"])
        self.assertEqual(ledger.issue_projects({"labels": ["project:blt-leaf", "bug"], "title": "x"}), ["blt-leaf"])
        self.assertFalse(ledger.is_open(ISSUE))
        self.assertTrue(ledger.closed_at(ISSUE).startswith("2026-"))

    def test_issues_reads_changed_folders_only(self):
        def answers(op, params):
            if op == "tree" and params["path"] == ".forkmesh/issues":
                return {"commit": "c", "entries": [{"type": "tree", "name": "closed"}]}
            if op == "tree":
                return {"entries": [{"type": "tree", "name": "3", "oid": "a"}]}
            return '{"number": 3, "title": "t"}'
        cache = {}
        client = FakeClient(answers)
        self.assertEqual([i["number"] for i in ledger.issues(client, cache)], [3])
        client.calls.clear()
        ledger.issues(client, cache)
        self.assertFalse([c for c in client.calls if c[0] == "blob"])

    def test_history_pages_by_parent_and_stops_at_since(self):
        def commit(n, day):
            return {"hash": f"h{n}", "parents": f"h{n + 1}", "date": f"2026-10-{day:02d}T00:00:00Z"}
        pages = {"": [commit(i, 20 - i // 10) for i in range(60)],
                 "h60": [commit(i, 14 - (i - 60) // 10) for i in range(60, 120)]}
        client = FakeClient(lambda op, params: {"commits": pages.get(params.get("ref", ""), [])})
        found = ledger.history(client, "blt-x", since=datetime(2026, 10, 12, tzinfo=timezone.utc))
        self.assertEqual(found[-1]["date"], "2026-10-12T00:00:00Z")
        self.assertEqual(client.calls[1][1]["ref"], "h60")


if __name__ == "__main__":
    unittest.main()
