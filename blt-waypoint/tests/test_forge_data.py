import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT, "scripts"))
import forge_urls  # noqa: E402
import generate_forge_data as gen  # noqa: E402

NOW = datetime(2026, 10, 18, 6, 29, tzinfo=timezone.utc)
TSV = "# folder\tname\taliases\nblt-leaf\tBLT-Leaf\t\nblt-legacy\tBLT-Legacy\tBLT-Core,blt-core,BLT,BLT-on-Cloudflare\n-\t-\tBLT-Claw\n"


def ago(days):
    return (NOW - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def commit(n, days, author="ann"):
    return {"hash": f"{n:040x}", "parents": f"{n + 1:040x}", "date": ago(days), "author": author, "subject": f"c{n}\nbody"}


class FakeClient:
    def __init__(self, history, issues=(), pulls=None):
        self.history = history
        self.issues = {str(i["number"]): i for i in issues}
        self.pulls = pulls
        self.calls = []

    def get(self, op, params=()):
        params = list(params)
        self.calls.append((op, params))
        if op == "history":
            args = dict(params)
            pages = self.history.get(args["path"], [])
            index = int(args.get("ref", "0") or 0, 16) if args.get("ref") else 0
            return {"commits": [c for c in pages if int(c["hash"], 16) >= index][:60]}
        raise AssertionError(op)

    def tree(self, path, ref=""):
        if path == ".forkmesh/issues":
            return {"commit": "m", "entries": [{"type": "tree", "name": "open"}]}
        if path == ".forkmesh/issues/open":
            return {"entries": [{"type": "tree", "name": n, "oid": f"o{n}"} for n in self.issues]}
        if path == ".forkmesh/pulls":
            return self.pulls
        raise AssertionError(path)

    def blobs(self, paths, ref=""):
        return {p: json.dumps(self.issues[p.split("/")[-2]]) for p in paths}


class GeneratorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.root = self.tmp.name
        os.makedirs(os.path.join(root, "scripts", "routing"))
        with open(os.path.join(root, "scripts", "routing", "projects.tsv"), "w") as f:
            f.write(TSV)
        os.makedirs(os.path.join(root, "blt-leaf", ".forkmesh"))
        with open(os.path.join(root, "blt-leaf", ".forkmesh", "info.json"), "w") as f:
            json.dump({"about": "PR readiness", "website": "https://leaf.owaspblt.org", "topics": ["github"]}, f)
        with open(os.path.join(root, "blt-leaf", "README.md"), "w") as f:
            f.write("x" * 42)
        open(os.path.join(root, "blt-leaf", "wrangler.toml"), "w").close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_build(self):
        leaf = [commit(1, 0.5, "owasp-blt-actions"), commit(2, 2), commit(3, 40, "bob"), commit(4, 200),
                commit(5, 400)]
        issues = [
            {"number": 7, "title": "[blt-leaf] broken", "status": "open", "labels": [], "authorName": "cat",
             "createdAt": 1792290689619, "updatedAt": 1792290689619, "events": []},
            {"number": 8, "title": "Other", "status": "open", "labels": ["project:blt-legacy"], "authorName": "dan",
             "createdAt": 1792290689000, "events": [{"type": "vote", "authorName": "x"}]},
            {"number": 9, "title": "blt-leaf: done", "status": "closed", "labels": [], "events": []},
            {"number": 10, "title": "general", "status": "open", "labels": [], "events": []},
        ]
        client = FakeClient({"blt-leaf": leaf}, issues)
        data = gen.build(client, root=self.root, now=NOW)
        leaf_row, core = data["repos"]
        self.assertEqual([r["folder"] for r in data["repos"]], ["blt-leaf", "blt-legacy"])
        self.assertEqual(leaf_row["html_url"], "https://git.owaspblt.org/BLT/tree/main/blt-leaf")
        self.assertEqual((leaf_row["commits_30d"], leaf_row["commits_90d"], leaf_row["commits_365d"]), (1, 2, 3))
        self.assertEqual(leaf_row["contributor_count"], 2)
        self.assertEqual(leaf_row["contributors"][0], {"login": "ann", "avatar_url": "", "html_url": "", "contributions": 2})
        self.assertEqual(leaf_row["last_commit_at"], ago(0.5))
        self.assertEqual(leaf_row["latest_commit"]["message"], "c1")
        self.assertTrue(leaf_row["latest_commit"]["html_url"].startswith("https://git.owaspblt.org/BLT/commit/"))
        self.assertEqual(sum(leaf_row["weekly_commits"]), 2)
        self.assertEqual(len(leaf_row["weekly_commits"]), 26)
        self.assertFalse(leaf_row["commits_truncated"])
        self.assertEqual(leaf_row["description"], "PR readiness")
        self.assertEqual(leaf_row["homepage"], "https://leaf.owaspblt.org")
        self.assertEqual(leaf_row["topics"], ["github"])
        self.assertEqual(leaf_row["readme_chars"], 42)
        self.assertTrue(leaf_row["has_wrangler_toml"])
        self.assertIsNone(leaf_row["stargazers_count"])
        self.assertIsNone(leaf_row["latest_release"])
        self.assertEqual(leaf_row["open_issues_count"], 1)
        self.assertEqual(leaf_row["latest_issue"]["html_url"], "https://git.owaspblt.org/BLT/issues/7")
        self.assertEqual(core["open_issues_count"], 1)
        self.assertEqual(core["latest_issue"]["votes"], 1)
        self.assertEqual(core["commits_365d"], 0)
        self.assertIsNone(core["latest_commit"])
        self.assertEqual(leaf_row["open_pr_count"], 0)
        self.assertIsNone(leaf_row["latest_pr"])
        self.assertEqual(sorted(i["number"] for i in data["open_issues"]), [7, 8, 10])
        general = [i for i in data["open_issues"] if i["number"] == 10][0]
        self.assertEqual((general["repo_name"], general["repo_html_url"]), ("BLT", "https://git.owaspblt.org/BLT"))
        self.assertEqual(data["cumulative"]["commits_365d"], 3)
        # History stopped at the first commit older than 365 days (one call per folder).
        self.assertEqual([p for op, p in client.calls if op == "history"][0][0], ("path", "blt-leaf"))

    def test_history_page_cap_marks_truncation(self):
        many = [commit(n, n * 0.1) for n in range(1, 200)]
        data = gen.build(FakeClient({"blt-leaf": many}), root=self.root, now=NOW, max_pages=2)
        row = data["repos"][0]
        self.assertTrue(row["commits_truncated"])
        self.assertEqual(row["commits_365d"], 120)

    def test_pulls_attributed_by_title(self):
        self.assertEqual(gen.pull_projects({"title": "[blt-leaf] x"}, {"blt-leaf"}), ["blt-leaf"])
        self.assertEqual(gen.pull_projects({"title": "x", "labels": ["project:blt-legacy"]}, {"blt-legacy"}), ["blt-legacy"])
        self.assertEqual(gen.pull_entry({"number": 3, "status": "merged", "authorName": "a", "ts": 1792290689619})["state"],
                         "merged")

    def test_deadline_stops_without_output(self):
        class Expired:
            requests = 0

            def tree(self, *a):
                raise gen.ledger.DeadlineExceeded()
        with self.assertRaises(gen.ledger.DeadlineExceeded):
            gen.build(Expired(), root=self.root, now=NOW)


class UrlTest(unittest.TestCase):
    def test_rewrite(self):
        index = forge_urls.folder_index()
        text = "see https://gitlab.com/owasp-blt/blt and https://gitlab.com/owasp-blt/toasty/-/issues/3 or https://gitlab.com/owasp-blt/nope"
        self.assertEqual(forge_urls.rewrite_text(text, index),
                         "see https://git.owaspblt.org/BLT/tree/main/blt-legacy and "
                         "https://git.owaspblt.org/BLT/tree/main/blt-toasty or https://git.owaspblt.org/BLT")
        self.assertEqual(forge_urls.resolve(".github", index), "dot_github")
        self.assertEqual(forge_urls.resolve("BLT-Github-Sportscaster", index), "blt-gitcaster")


class CommittedFilesTest(unittest.TestCase):
    def test_no_gitlab_project_urls(self):
        for path in ("data/github_archive.json", "public/forge_data.json", "public/index.html",
                     "public/issues.html", "public/screenshots.html", "public/script.js"):
            with open(os.path.join(PROJECT, path), encoding="utf-8") as f:
                self.assertNotIn("gitlab.com/owasp-blt", f.read(), path)

    def test_the_pages_read_only_the_forge_data(self):
        for name in ("index.html", "issues.html", "screenshots.html", "script.js"):
            with open(os.path.join(PROJECT, "public", name), encoding="utf-8") as f:
                text = f.read()
            for old in ("github_data.json", "main_data", "imgs/screenshots"):
                self.assertNotIn(old, text, f"{name} still reads {old}")

    def test_forge_data_shape(self):
        with open(os.path.join(PROJECT, "public", "forge_data.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["source"], "forge")
        self.assertTrue(data["repos"])
        for key in ("folder", "html_url", "commits_30d", "commits_90d", "commits_365d", "open_issues_count"):
            self.assertIn(key, data["repos"][0])


if __name__ == "__main__":
    unittest.main()
