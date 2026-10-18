"""Tests for the git.owaspblt.org (ForkMesh) source, the refresh budget and Slack activity.

Run from blt-hackathons/:  python3 -m unittest discover -s test -p 'test_*.py'
No network: a fake opener plays the ForkMesh and Slack APIs.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import forkmesh_source as fm  # noqa: E402
import slack_activity  # noqa: E402

API = "https://git.example/api/repo/owasp-blt/BLT"
WEB = "https://git.example/BLT"
MS = lambda iso: int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)  # noqa: E731


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeForkMesh:
    """Serves tree/blobs/compare from an in-memory map {ref: {path: text}}."""

    def __init__(self):
        self.files = {"forkmesh/pulls": {}, "main": {}}
        self.pull_refs = {}
        self.calls = []

    def oid(self, ref, folder):
        # A folder's oid changes whenever any file below it changes, like a git tree id.
        return str(hash(tuple(sorted((p, t) for p, t in self.files[ref].items() if p.startswith(folder + "/")))))

    def __call__(self, request, timeout=None):
        url = urlparse(request.full_url)
        op = url.path.rsplit("/", 1)[1]
        query = parse_qs(url.query)
        self.calls.append(op)
        ref = (query.get("ref") or ["main"])[0]
        ref = {"commit-pulls": "forkmesh/pulls", "commit-main": "main"}.get(ref, ref)
        if op == "tree":
            path = query["path"][0]
            files = self.files.get(ref)
            if files is None or not any(p.startswith(path + "/") for p in files):
                raise HTTPError(request.full_url, 404, "not found", {}, None)
            names = {}
            for p in files:
                if p.startswith(path + "/"):
                    rest = p[len(path) + 1:].split("/")
                    names[rest[0]] = "tree" if len(rest) > 1 else "blob"
            body = {"commit": "commit-pulls" if ref == "forkmesh/pulls" else "commit-main",
                    "entries": [{"name": n, "type": t, "oid": self.oid(ref, f"{path}/{n}") if t == "tree" else "x"}
                                for n, t in sorted(names.items())]}
            if path == ".forkmesh/pulls":
                body["pullRefs"] = self.pull_refs
        elif op == "blobs":
            files = self.files.get(ref) or {}
            body = {"blobs": {p: ({"content": files[p]} if p in files else None) for p in query["path"]}}
        elif op == "compare":
            body = {"commits": "diff --git a/blt-leaf/app.py b/blt-leaf/app.py\n"}
        else:
            raise HTTPError(request.full_url, 404, "not found", {}, None)
        return Response(json.dumps(body).encode())


def pull_md(number, title, status="open", ts="2026-11-05T10:00:00Z", author="alice", extra=""):
    return (f"---\nschema: forkmesh-pull-v1\nnumber: {number}\ntitle: {title}\nbase: main\nhead: x\n"
            f"status: {status}\nts: {MS(ts)}\nauthor: key-{author}\nauthorName: {author}\nsig: s{number}\n{extra}---\n\nbody\n")


def event_md(kind, author, ts, state=""):
    state_line = f"state: {state}\n" if state else ""
    return f"---\ntype: {kind}\nid: {kind}-{author}-{ts}\nauthor: key-{author}\nauthorName: {author}\nts: {MS(ts)}\n{state_line}---\n\ntext\n"


def issue_json(number, title, labels=(), status="open", created="2026-11-03T00:00:00Z"):
    return json.dumps({"number": number, "title": title, "labels": list(labels), "status": status,
                       "authorName": "carol", "createdAt": MS(created), "updatedAt": MS(created),
                       "events": [{"type": "status", "state": "closed", "ts": MS("2026-11-04T00:00:00Z")}]
                       if status == "closed" else []})


def sample_repo():
    fake = FakeForkMesh()
    pulls = fake.files["forkmesh/pulls"]
    merged = "mergedAt: %d\n" % MS("2026-11-06T12:00:00Z")
    pulls[".forkmesh/pulls/1/pull.md"] = pull_md(1, "Fix leaf", "merged", extra=merged)
    pulls[".forkmesh/pulls/1/changes.patch"] = ("diff --git a/blt-leaf/a.py b/blt-leaf/a.py\n"
                                                "diff --git a/.forkmesh/blt-leaf--ci.yml b/.forkmesh/blt-leaf--ci.yml\n")
    pulls[".forkmesh/pulls/1/0002-review.md"] = event_md("review", "bob", "2026-11-06T09:00:00Z", "approved")
    pulls[".forkmesh/pulls/1/0003-comment.md"] = event_md("comment", "alice", "2026-11-06T09:30:00Z")
    pulls[".forkmesh/pulls/2/pull.md"] = pull_md(2, "blt-jobs: tidy", author="dave")  # no diff: title prefix
    pulls[".forkmesh/pulls/3/pull.md"] = pull_md(3, "docs only")
    pulls[".forkmesh/pulls/3/changes.patch"] = "diff --git a/README.md b/README.md\n"
    pulls[".forkmesh/pulls/4/pull.md"] = pull_md(4, "branch pull", "merged", author="erin",
                                                 extra="derive: branch\nmergeBase: aaa\nmergeHead: bbb\n" + merged)
    pulls[".forkmesh/pulls/5/pull.md"] = pull_md(5, "old", ts="2026-01-01T00:00:00Z")
    pulls[".forkmesh/pulls/5/changes.patch"] = "diff --git a/blt-leaf/x b/blt-leaf/x\n"
    main = fake.files["main"]
    main[".forkmesh/issues/open/1/issue-1.json"] = issue_json(1, "Broken page", labels=["blt-leaf"])
    main[".forkmesh/issues/closed/2/issue-2.json"] = issue_json(2, "[blt-jobs] crash", status="closed")
    main[".forkmesh/issues/open/3/issue-3.json"] = issue_json(3, "General question")
    return fake


START = datetime(2026, 11, 1, tzinfo=timezone.utc)
END = datetime(2027, 5, 9, 23, 59, 59, tzinfo=timezone.utc)


def client(fake, deadline=None):
    return fm.ForkMeshClient("https://git.example", "owasp-blt", "BLT", deadline=deadline,
                             opener=fake, sleep=lambda s: None)


class AttributionTests(unittest.TestCase):
    def test_paths_titles_and_labels(self):
        self.assertEqual(fm.path_project("blt-leaf/src/a.py"), "blt-leaf")
        self.assertEqual(fm.path_project(".forkmesh/blt-leaf--ci.yml"), "blt-leaf")
        self.assertEqual(fm.path_project("README.md"), fm.SHARED)
        self.assertEqual(fm.path_project(".forkmesh/ci.yml"), fm.SHARED)
        self.assertEqual(fm.title_project("blt-leaf: fix"), "blt-leaf")
        self.assertEqual(fm.title_project("[BLT-Leaf] fix"), "blt-leaf")
        self.assertEqual(fm.title_project("Fix: thing"), "fix")
        self.assertEqual(fm.label_projects(["project:blt-jobs", {"name": "Bug"}]), ["blt-jobs", "bug"])
        folders = {"blt-leaf", "blt-jobs"}
        self.assertEqual(fm.attributed(["blt-leaf", fm.SHARED], "", folders), ["blt-leaf"])
        self.assertEqual(fm.attributed([fm.SHARED], "blt-leaf", folders), [])  # the diff decides
        self.assertEqual(fm.attributed([], "blt-jobs", folders), ["blt-jobs"])
        self.assertEqual(fm.attributed([], "fix", folders), [])
        self.assertEqual(fm.attributed([], "", {"*"}), [fm.SHARED])


class SyncTests(unittest.TestCase):
    def test_full_sync_and_hackathon_inputs(self):
        fake = sample_repo()
        cache, complete = fm.sync_repository(client(fake), None, WEB, ["blt-leaf", "blt-jobs"])
        self.assertTrue(complete)
        pull = cache["pulls"]["1"]["record"]
        self.assertEqual(pull["pathProjects"], ["blt-leaf"])
        self.assertEqual(pull["merged_at"], "2026-11-06T12:00:00Z")
        self.assertEqual(pull["user"]["html_url"], "https://git.example/@alice")
        self.assertEqual(pull["html_url"], f"{WEB}/pulls/1")
        self.assertEqual([r["state"] for r in pull["reviews"]], ["APPROVED", "COMMENTED"])
        self.assertEqual(cache["pulls"]["4"]["record"]["pathProjects"], ["blt-leaf"])  # via compare
        self.assertEqual(cache["issues"]["2"]["record"]["closed_at"], "2026-11-04T00:00:00Z")

        prs, reviews, issues, repos, repo_data = fm.hackathon_inputs(cache, ["blt-leaf", "blt-jobs"], START, END, WEB)
        self.assertEqual(sorted(p["number"] for p in prs), [1, 2, 4])  # 3 touches no project, 5 is too old
        self.assertEqual({p["number"]: p["repository"] for p in prs}[2], "blt-jobs")
        self.assertEqual(sorted(i["number"] for i in issues), [1, 2])
        self.assertEqual(repos, ["blt-jobs", "blt-leaf"])
        self.assertEqual(repo_data[1]["html_url"], f"{WEB}/tree/main/blt-leaf")
        self.assertEqual(len(reviews), 2)

        import fetch_stats
        stats = fetch_stats.process_hackathon_stats(prs, reviews, issues, START, END, repos)
        self.assertEqual(stats["mergedPRs"], 2)
        self.assertEqual(stats["repoStats"]["blt-leaf"]["merged"], 2)
        self.assertEqual([p["username"] for p in stats["reviewLeaderboard"]], ["bob"])  # alice reviewed herself

    def test_incremental_rereads_only_changed_folders(self):
        fake = sample_repo()
        cache, _ = fm.sync_repository(client(fake), None, WEB)
        fake.calls.clear()
        cache, complete = fm.sync_repository(client(fake), cache, WEB)
        self.assertTrue(complete)
        self.assertEqual(fake.calls, ["tree", "tree", "tree", "tree"])  # listings only
        fake.files["forkmesh/pulls"][".forkmesh/pulls/2/0002-review.md"] = event_md(
            "review", "bob", "2026-11-07T00:00:00Z", "changes_requested")
        fake.calls.clear()
        cache, _ = fm.sync_repository(client(fake), cache, WEB)
        self.assertEqual(fake.calls.count("tree"), 5)  # 4 listings + pull 2's folder
        self.assertEqual(cache["pulls"]["2"]["record"]["reviews"][0]["state"], "CHANGES_REQUESTED")
        del fake.files["main"][".forkmesh/issues/open/3/issue-3.json"]
        cache, _ = fm.sync_repository(client(fake), cache, WEB)
        self.assertNotIn("3", cache["issues"])

    def test_deadline_keeps_progress_and_resumes(self):
        fake = sample_repo()
        ticks = iter(range(1000))
        deadline = fm.Deadline(6, clock=lambda: next(ticks))  # allows a few requests only
        cache, complete = fm.sync_repository(client(fake, deadline), None, WEB)
        self.assertFalse(complete)
        self.assertFalse(cache["complete"])
        done = len(cache["pulls"])
        self.assertLess(done, 5)
        fake.calls.clear()
        cache, complete = fm.sync_repository(client(fake), cache, WEB)
        self.assertTrue(complete)
        self.assertEqual(len(cache["pulls"]), 5)
        # Pulls read in the first run are not read again.
        self.assertEqual(fake.calls.count("blobs"), (5 - done) + 1)  # remaining pulls + issues

    def test_missing_ledger_means_no_pulls(self):
        fake = FakeForkMesh()
        cache, complete = fm.sync_repository(client(fake), None, WEB)
        self.assertTrue(complete)
        self.assertEqual(cache["pulls"], {})

    def test_branch_only_pull_from_pull_refs(self):
        fake = sample_repo()
        fake.files["forkmesh/pull/9"] = {".forkmesh/pulls/9/pull.md": pull_md(9, "blt-leaf: new")}
        fake.pull_refs = {"9": "forkmesh/pull/9"}
        cache, _ = fm.sync_repository(client(fake), None, WEB)
        self.assertEqual(cache["pulls"]["9"]["record"]["titleProject"], "blt-leaf")


class SlackOpener:
    def __init__(self, totals, fail_after=None):
        self.totals = totals
        self.queries = []
        self.fail_after = fail_after

    def __call__(self, request, timeout=None):
        query = parse_qs(urlparse(request.full_url).query)["query"][0]
        self.queries.append((request.headers.get("Authorization"), query))
        if self.fail_after is not None and len(self.queries) > self.fail_after:
            raise HTTPError(request.full_url, 429, "slow down", {"Retry-After": "30"}, None)
        who = query.split()[0][len("from:"):].strip("@<>")
        return Response(json.dumps({"ok": True, "messages": {"total": self.totals.get(who, 0)}}).encode())


class SlackTests(unittest.TestCase):
    mapping = {"alice": {"owasp": "alice.dev", "blt": "alice"}, "bob": {"owasp": "U012ABCDEF", "blt": None}}

    def run_refresh(self, state, env, now, opener):
        return slack_activity.refresh("x", self.mapping, START, END, state, env=env, now=now,
                                      opener=opener, sleep=lambda s: None)

    def test_counts_both_workspaces_with_date_range(self):
        opener = SlackOpener({"alice.dev": 5, "alice": 2, "U012ABCDEF": 7})
        env = {"SLACK_TOKEN_OWASP": "o", "SLACK_TOKEN_BLT": "b"}
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        state = {}
        block = self.run_refresh(state, env, now, opener)
        self.assertTrue(block["enabled"])
        self.assertEqual(block["totalMessages"], 14)
        rows = {p["username"]: p for p in block["participants"]}
        self.assertEqual((rows["alice"]["owasp"], rows["alice"]["blt"], rows["alice"]["total"]), (5, 2, 7))
        self.assertIsNone(rows["bob"]["blt"])  # no BLT handle: shown as "—"
        self.assertIn(("Bearer o", "from:@alice.dev after:2026-10-31 before:2026-11-11"), opener.queries)
        self.assertIn(("Bearer o", "from:<@U012ABCDEF> after:2026-10-31 before:2026-11-11"), opener.queries)
        self.assertEqual(len(opener.queries), 3)
        # Within the refresh interval nothing is asked again; the counts stay.
        again = self.run_refresh(state, env, now + timedelta(hours=2), opener)
        self.assertEqual(len(opener.queries), 3)
        self.assertEqual(again["totalMessages"], 14)

    def test_missing_tokens_and_not_started(self):
        block = self.run_refresh({}, {}, datetime(2026, 11, 10, tzinfo=timezone.utc), SlackOpener({}))
        self.assertFalse(block["enabled"])
        opener = SlackOpener({})
        block = self.run_refresh({}, {"SLACK_TOKEN_BLT": "b"}, datetime(2026, 10, 20, tzinfo=timezone.utc), opener)
        self.assertEqual(opener.queries, [])
        self.assertEqual(block["servers"], ["blt"])
        self.assertEqual(block["totalMessages"], 0)

    def test_rate_limit_and_call_cap_continue_next_run(self):
        env = {"SLACK_TOKEN_OWASP": "o", "SLACK_TOKEN_BLT": "b", "SLACK_MAX_CALLS": "2"}
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        state = {}
        opener = SlackOpener({"alice.dev": 1, "alice": 1, "U012ABCDEF": 1})
        self.run_refresh(state, env, now, opener)
        self.assertEqual(sorted(state["users"]), ["alice"])  # bob waits for the next run
        self.run_refresh(state, env, now, opener)
        self.assertEqual(sorted(state["users"]), ["alice", "bob"])
        limited = SlackOpener({}, fail_after=0)
        later = now + timedelta(days=2)
        block = self.run_refresh(state, env, later, limited)  # 429: keep the old counts
        self.assertEqual(block["totalMessages"], 3)

    def test_mapping_file_and_attach(self):
        try:
            import yaml  # noqa: F401
        except ModuleNotFoundError:  # PyYAML is installed by the workflow, not by CI
            self.skipTest("PyYAML not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "slack.yml")
            Path(path).write_text("slack:\n  Alice: alice.dev\n  bob: {owasp: '@bob'}\n  nobody: {}\n")
            mapping = slack_activity.load_mapping(path)
        self.assertEqual(mapping, {"alice": {"owasp": "alice.dev", "blt": "alice.dev"},
                                   "bob": {"owasp": "bob", "blt": None}})
        stats = {"leaderboard": [{"username": "Alice"}, {"username": "zed"}]}
        slack_activity.attach(stats, {"enabled": True, "participants": [{"username": "alice", "total": 4}]})
        self.assertEqual(stats["leaderboard"][0]["slackMessages"], 4)
        self.assertNotIn("slackMessages", stats["leaderboard"][1])


class ConfigTests(unittest.TestCase):
    def test_project_folders_match_routing_table(self):
        root = HERE.parents[1]
        table = [line.split("\t")[0] for line in (root / "scripts/routing/projects.tsv").read_text().splitlines()
                 if line and not line.startswith("#") and not line.startswith("-\t")]
        config = (HERE.parent / "public/js/hackathons-config.js").read_text()
        block = config[config.index("const OWASP_BLT_PROJECT_FOLDERS"):]
        block = block[:block.index("];")]
        listed = [line.strip().strip('",') for line in block.splitlines()[1:] if line.strip()]
        self.assertEqual(sorted(listed), sorted(table))


if __name__ == "__main__":
    unittest.main()
