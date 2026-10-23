"""Unit tests for scripts/generate_leaderboard.py (no network: ledger records are built here)."""
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import generate_leaderboard as gen  # noqa: E402


def issue(number, title, labels, author="ann", status="open", body="", comments=(), votes=()):
    events = [{"type": "open", "id": f"o{number}", "ts": 1792290689619 + number, "authorName": author, "body": body}]
    events += [{"type": "comment", "id": f"c{number}-{i}", "ts": 1792290699619 + i, "authorName": who, "body": text}
               for i, (who, text) in enumerate(comments)]
    events += [{"type": "vote", "id": f"v{number}-{i}", "ts": 1792290799619 + i, "authorName": who}
               for i, who in enumerate(votes)]
    return {"number": number, "title": title, "labels": labels, "status": status, "authorName": author,
            "createdAt": 1792290689619 + number * 60000, "events": events}


BODY = "### URL\n\nhttps://www.example.com/page\n\n### Description\n\n![shot](https://img.example/a.png)\n"


class LeaderboardTest(unittest.TestCase):
    def test_only_blt_pages_bug_reports_count(self):
        issues = [
            issue(1, "[blt-pages] Broken login", ["bug"], body=BODY, comments=[("bob", "confirmed")], votes=["cat"]),
            issue(2, "Broken thing", ["bug", "blt-pages"], author="bob", status="closed", body=BODY),
            issue(3, "[blt-leaf] Unrelated bug", ["bug"]),
            issue(4, "[blt-pages] A feature", ["enhancement"]),
        ]
        bugs = gen.bug_reports(issues)
        self.assertEqual([b["number"] for b in bugs], [2, 1])
        payload = gen.build_payload(bugs, now=datetime(2026, 10, 18, tzinfo=timezone.utc))
        self.assertEqual((payload["total_bugs"], payload["open_bugs"], payload["closed_bugs"]), (2, 1, 1))
        self.assertEqual(payload["top_domains"], [{"rank": 1, "domain": "example.com", "count": 2}])
        self.assertEqual([e["login"] for e in payload["leaderboard"]], ["ann", "bob"])
        self.assertEqual(payload["top_commenters"][0]["login"], "bob")
        recent = payload["recent_bugs"][0]
        self.assertEqual(recent["html_url"], "https://git.owaspblt.org/BLT/issues/1")
        self.assertEqual(recent["image_url"], "https://img.example/a.png")
        self.assertEqual(recent["reactions"], {"+1": 1})
        self.assertEqual(recent["user"]["profile_url"], "https://git.owaspblt.org/@ann")
        self.assertEqual(recent["latest_comment"]["user"]["login"], "bob")

    def test_bots_are_not_on_the_leaderboard(self):
        bugs = gen.bug_reports([issue(5, "blt-pages: fix x", ["bug", "blt-pages"], author="blt-tasks[bot]"),
                                issue(6, "[blt-pages] Broken", ["bug"], author="dee")])
        payload = gen.build_payload(bugs, now=datetime(2026, 10, 18, tzinfo=timezone.utc))
        self.assertEqual(payload["total_bugs"], 2)
        self.assertEqual([e["login"] for e in payload["leaderboard"]], ["dee"])

    def test_pages_link_to_the_forge(self):
        html = gen.render_leaderboard_rows([]) + gen.render_commenters_rows([])
        self.assertIn("https://git.owaspblt.org/BLT/issues/new", html)
        self.assertIn("https://git.owaspblt.org/BLT/issues?label=blt-pages", html)
        self.assertNotIn("gitlab", html.lower())

    def test_leaders_nominations_from_issues(self):
        body = ("## BLT Leadership Nomination\n\n**Election:** 2027 Leads (blt-2027)\n**Project:** BLT-Pages\n"
                "**Role:** Lead\n**Nominee:** @bob\n\n### Statement\nI will help.\n\n### Skills\nJS, Security\n\n"
                "### Prior Contributions\n_Not provided_\n\n---\n")
        issues = [issue(9, "[NOMINATION] 2027 Leads — Lead: bob", ["accepted"], author="bob", body=body,
                        votes=["ann", "ann", "cat"])]
        previous = {"elections": [{"id": "blt-2027"}], "nominations": [{"id": "manual"}, {"id": "x", "issue_number": 9}]}
        leaders = gen.build_leaders(issues, previous, [("blt-pages", "BLT-Pages")])
        self.assertEqual(leaders["elections"], [{"id": "blt-2027"}])
        self.assertEqual(leaders["projects"][0]["repo_url"], "https://git.owaspblt.org/BLT/tree/main/blt-pages")
        manual, nom = leaders["nominations"]
        self.assertEqual(manual, {"id": "manual"})
        self.assertEqual((nom["election_id"], nom["project_id"], nom["role"]), ("blt-2027", "blt-pages", "Lead"))
        self.assertEqual((nom["nominee_login"], nom["status"], nom["self_nominated"]), ("bob", "accepted", True))
        self.assertEqual(nom["voters"], ["ann", "cat"])
        self.assertEqual(nom["skills"], ["JS", "Security"])
        self.assertEqual(nom["contributions"], "")


if __name__ == "__main__":
    unittest.main()
