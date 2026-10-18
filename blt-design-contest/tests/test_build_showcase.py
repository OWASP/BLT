"""Unit tests for scripts/build_showcase.py (no network: issue records are built here)."""
import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT, "scripts"))

import build_showcase as bs  # noqa: E402


def record(number, title, labels=(), body="", status="open", votes=0, events=(), author="alice"):
    opened = {"type": "open", "id": f"open-{number}", "ts": 1792290689619, "body": body,
              "author": author, "authorName": author}
    return {"number": number, "title": title, "labels": [{"name": n} for n in labels],
            "status": status, "votes": votes, "createdAt": 1792290689619, "authorName": author,
            "events": [opened, *events]}


def comment(body, name, ts=1792290700000):
    return {"type": "comment", "id": f"c-{name}-{ts}", "body": body, "author": name, "authorName": name, "ts": ts}


def vote(name):
    return {"type": "vote", "id": f"v-{name}", "author": name, "authorName": name, "ts": 1792290700000}


def filled(template, **answers):
    with open(os.path.join(PROJECT, "issue-templates", template), encoding="utf-8") as fh:
        text = fh.read()
    for heading, answer in answers.items():
        text = text.replace(f"### {heading}\n", f"### {heading}\n\n{answer}\n", 1)
    return text


class SubmissionTests(unittest.TestCase):
    def test_contest_from_label_or_title_prefix(self):
        logo = record(1, "[blt-design-contest] [Logo] Shield")
        self.assertEqual(bs.submission_contest(logo)["id"], "blt-logo")
        labelled = record(2, "My homepage", labels=["homepage-submission"])
        self.assertEqual(bs.submission_contest(labelled)["id"], "blt-homepage")
        project = record(3, "[Video Meme] Bugs", labels=["project:blt-design-contest"])
        self.assertEqual(bs.submission_contest(project)["id"], "blt-video-meme")

    def test_not_submissions(self):
        self.assertIsNone(bs.submission_contest(record(4, "[Logo] not attributed")))
        self.assertIsNone(bs.submission_contest(record(5, "[blt-design-contest] [Logo] x", status="closed")))
        self.assertIsNone(bs.submission_contest(record(6, "[blt-design-contest] Declare winner: logo")))
        self.assertIsNone(bs.submission_contest(record(7, "[blt-pages] [Logo] other project")))


class VoteTests(unittest.TestCase):
    def test_native_votes_plus_distinct_plus_one_comments(self):
        r = record(1, "[blt-design-contest] [Logo] x", events=[
            vote("bob"), vote("carol"),
            comment("+1", "bob"),        # already voted
            comment(" +1 ", "dave"),     # counts
            comment(":+1:", "dave", 1792290900000),  # same account again
            comment("+1", "alice"),      # the author
            comment("+1 nice", "erin"),  # not just +1
        ])
        self.assertEqual(sorted(bs.plus_one_voters(r)), ["bob", "dave"])
        self.assertEqual(bs.vote_total(r), 3)

    def test_votes_field_is_a_floor(self):
        self.assertEqual(bs.vote_total(record(1, "x", votes=4)), 4)


class BodyTests(unittest.TestCase):
    def test_template_body(self):
        body = filled("logo-submission.md", **{
            "Preview Image": "![logo](/BLT/uploads/logo.png)",
            "Description": "A shield.",
        }).replace("https://\n", "https://example.com/figma\n", 1)
        fields = bs.parse_issue_body(body)
        self.assertEqual(bs.extract_preview_url(fields, body), "https://git.owaspblt.org/BLT/uploads/logo.png")
        self.assertEqual(bs.extract_design_url(fields), "https://example.com/figma")
        self.assertEqual(bs.extract_category(fields), "Logo / Brand Identity")
        self.assertEqual(bs.extract_description(fields), "A shield.")

    def test_unfilled_template_has_no_preview_or_link(self):
        body = filled("logo-submission.md")
        fields = bs.parse_issue_body(body)
        self.assertEqual(bs.extract_preview_url(fields, body), "")
        self.assertEqual(bs.extract_design_url(fields), "")
        self.assertEqual(bs.extract_description(fields), "")

    def test_gitlab_style_category_list(self):
        fields = bs.parse_issue_body("### Video Meme Category\n\n- Humorous\n- Explainer\n")
        self.assertEqual(bs.extract_category(fields), "Humorous")

    def test_all_templates_parse(self):
        for name in os.listdir(os.path.join(PROJECT, "issue-templates")):
            if name.endswith("-submission.md"):
                fields = bs.parse_issue_body(filled(name))
                self.assertIn("preview_image", fields, name)
                self.assertIn("description", fields, name)


class NormalizeTests(unittest.TestCase):
    def test_forge_issue(self):
        r = record(12, "[blt-design-contest] [Logo] Shield", body="### Description\n\nHi",
                   events=[comment("Love it", "bob"), comment("+1", "carol", 1792290800000)])
        issue = bs.normalize_forge_issue(r)
        self.assertEqual(issue["title"], "[Logo] Shield")
        self.assertEqual(issue["html_url"], "https://git.owaspblt.org/BLT/issues/12")
        self.assertEqual(issue["user"]["html_url"], "https://git.owaspblt.org/@alice")
        self.assertEqual(issue["votes"], 1)
        self.assertEqual(issue["comments"], 1)
        self.assertEqual(issue["last_comment"]["body"], "Love it")
        self.assertEqual(issue["created_at"], "2026-10-18T02:31:29Z")


class PageTests(unittest.TestCase):
    def test_pages(self):
        records = [
            record(20, "[blt-design-contest] [Logo] Shield", body="### Description\n\nA shield",
                   events=[vote("bob")]),
            record(21, "[blt-design-contest] [Logo] Winner", labels=["winner"]),
            record(22, "[blt-design-contest] [Logo] Closed", status="closed"),
        ]
        archive = [{"contest": "blt-logo", "number": 85, "title": "Old", "created_at": "2026-03-03T20:41:16Z",
                    "votes": 18, "preview_url": "assets/entries/x.png", "author": {"login": "kaif"}}]
        data = bs.group_submissions(records, archive)
        logo = next(d for d in data if d["config"]["id"] == "blt-logo")
        self.assertEqual([i["number"] for i in logo["issues"]], [21, 20, 85])
        self.assertEqual(logo["winner_count"], 1)
        with tempfile.TemporaryDirectory() as out:
            with contextlib.redirect_stdout(io.StringIO()):
                written = bs.write_pages(data, out, "18 Oct 2026 10:00 UTC")
            self.assertEqual(len(written), 2 + len(bs.CONTESTS))
            with open(os.path.join(out, "blt-logo.html"), encoding="utf-8") as fh:
                page = fh.read()
        self.assertIn('href="https://git.owaspblt.org/BLT/issues/20"', page)
        self.assertIn("Vote on the issue", page)
        self.assertIn('data-votes="1"', page)
        self.assertIn('data-votes="18"', page)
        self.assertIn("GitLab archive", page)
        self.assertNotIn("Closed", page)
        self.assertNotIn("gitlab.com/api", page)
        self.assertNotIn("fetch(", page)


class ArchiveTests(unittest.TestCase):
    def test_archive_is_complete_and_local(self):
        entries = bs.load_archive()
        self.assertEqual(len(entries), 45)
        ids = {c["id"] for c in bs.CONTESTS}
        for entry in entries:
            self.assertIn(entry["contest"], ids)
            self.assertTrue(os.path.exists(os.path.join(PROJECT, "public", entry["preview_url"])), entry["preview_url"])
        self.assertEqual(sum(1 for e in entries if e["winner"]), 1)


if __name__ == "__main__":
    unittest.main()
