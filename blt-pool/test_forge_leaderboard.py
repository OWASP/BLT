"""Tests for the forge (git.owaspblt.org) source of the PR leaderboard.

Covers ledger parsing, aggregation, attribution, identities, the incremental cursor and the
empty-ledger case (services/forge_leaderboard.py), plus the /leaderboard and /api/leaderboard
routes and the blt-cron task in worker.py. D1 is played by sqlite3 with the real migrations.
"""

import asyncio
import json
import pathlib
import sqlite3
import types
import unittest
from unittest.mock import AsyncMock, patch

from test_worker import _worker  # installs the js / pyodide stubs and loads worker.py
from services import forge_leaderboard as fl

ROOT = pathlib.Path(__file__).parent
ORG = "OWASP-BLT"
API = "https://git.owaspblt.org/api/repo/owasp-blt/BLT"
NOW = 1792000000  # 2026-10-14


def run(coro):
    return asyncio.run(coro)


def ms(iso):
    return fl.to_ms(iso)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeD1:
    """The D1 binding API (prepare/bind/all/run/batch) over sqlite3 with blt-pool's migrations."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        for path in sorted((ROOT / "migrations").glob("*.sql")):
            self.conn.executescript(path.read_text())
        self.reads = 0
        self.writes = 0
        self.batches = 0

    def prepare(self, sql):
        return FakeStatement(self, sql, ())

    async def batch(self, statements):
        self.batches += 1
        with self.conn:
            for stmt in statements:
                self.writes += 1
                self.conn.execute(stmt.sql, stmt.params)

    def rows(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]


class FakeStatement:
    def __init__(self, db, sql, params):
        self.db, self.sql, self.params = db, sql, params

    def bind(self, *params):
        return FakeStatement(self.db, self.sql, params)

    async def all(self):
        self.db.reads += 1
        return {"results": self.db.rows(self.sql, self.params)}

    async def run(self):
        self.db.writes += 1
        cur = self.db.conn.execute(self.sql, self.params)
        self.db.conn.commit()
        return {"meta": {"changes": cur.rowcount}}


class FakeForge:
    """Answers forge API GETs from an in-memory ledger."""

    def __init__(self, roster=None):
        self.roster = roster
        self.ledger = None  # None: the ledger branch does not exist (404)
        self.commit = "c1"
        self.pull_refs = {}
        self.unlisted = set()  # pulls the aggregate ledger has not caught up with
        self.calls = []

    def set_pull(self, number, files, oid=None):
        if self.ledger is None:
            self.ledger = {}
        self.ledger[str(number)] = {"oid": oid or f"oid-{number}-{len(self.calls)}", "files": files}

    async def __call__(self, url):
        self.calls.append(url)
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(url)
        op = parsed.path.rsplit("/", 1)[-1]
        q = parse_qs(parsed.query)
        if op == "raw":
            return (200, self.roster) if self.roster is not None else (404, None)
        if self.ledger is None:
            return 404, None
        if op == "tree":
            path = q["path"][0]
            if path == ".forkmesh/pulls":
                entries = [{"name": n, "type": "tree", "oid": p["oid"]} for n, p in self.ledger.items()
                           if n not in self.unlisted]
                return 200, {"commit": self.commit, "entries": entries, "pullRefs": self.pull_refs}
            number = path.rsplit("/", 1)[-1]
            files = self.ledger.get(number, {}).get("files", {})
            return 200, {"entries": [{"name": n, "type": "blob"} for n in files]}
        if op == "blobs":
            blobs = {}
            for path in q["path"]:
                _, _, number, name = path.split("/", 3)
                text = self.ledger.get(number, {}).get("files", {}).get(name)
                if text is not None:
                    blobs[path] = {"content": text}
            return 200, {"blobs": blobs}
        if op == "compare":
            return 200, {"commits": "diff --git a/blt-leaf/x.py b/blt-leaf/x.py\n"}
        return 404, None


def pull_md(title, status, author, opened, merged=None, extra=""):
    merged_line = f"mergedAt: {ms(merged)}\n" if merged else ""
    return (f"---\ntitle: {title}\nstatus: {status}\nts: {ms(opened)}\nauthor: key-{author}\n"
            f"authorName: {author}\n{merged_line}{extra}---\n\nbody\n")


def event_md(kind, author, when, body="text", state=""):
    state_line = f"state: {state}\n" if state else ""
    return f"---\ntype: {kind}\nid: {kind}-{author}-{when}\nauthorName: {author}\nts: {ms(when)}\n{state_line}---\n\n{body}\n"


ROSTER = {"contributors": [
    {"slug": "alice", "name": "Alice Example", "login": "alice-forge", "github": "Alice",
     "avatar": ".forkmesh/contributors/alice.png", "source": "instance"},
    {"slug": "bob", "name": "Bob B", "login": "bob", "github": "bob", "avatar": ".forkmesh/contributors/bob.png"},
    {"slug": "git-old", "name": "Old Timer", "login": None, "github": None, "avatar": ""},
    {"slug": "dependabot", "name": "dependabot[bot]", "login": "dependabot[bot]", "github": "dependabot[bot]"},
]}


# ---------------------------------------------------------------------------
# Parsing and attribution
# ---------------------------------------------------------------------------

class TestParsing(unittest.TestCase):
    def test_front_matter(self):
        values, body = fl.parse_front_matter("---\ntitle: a: b\nstatus: open\n---\n\nhello")
        self.assertEqual(values, {"title": "a: b", "status": "open"})
        self.assertEqual(body.strip(), "hello")
        self.assertEqual(fl.parse_front_matter("no front matter"), ({}, "no front matter"))

    def test_to_ms(self):
        self.assertEqual(fl.to_ms("1792000000000"), 1792000000000)
        self.assertEqual(fl.to_ms("2026-10-01T00:00:00Z"), 1790812800000)
        self.assertEqual(fl.to_ms(None), 0)
        self.assertEqual(fl.to_ms("garbage"), 0)

    def test_parse_merged_pull(self):
        pull = fl.parse_pull(7, pull_md("blt-pool: fix", "merged", "bob", "2026-09-28T10:00:00Z",
                                        merged="2026-10-02T10:00:00Z"),
                             {"0001-review.md": event_md("review", "alice-forge", "2026-09-30T00:00:00Z", state="approved")})
        self.assertEqual(pull["status"], "merged")
        self.assertEqual(pull["author"], "bob")
        self.assertEqual(fl.month_of(pull["opened"]), "2026-09")
        self.assertEqual(fl.month_of(pull["merged"]), "2026-10")
        self.assertEqual(pull["events"][0]["type"], "review")
        self.assertEqual(pull["projects"], ["blt-pool"])

    def test_unreadable_pull(self):
        self.assertIsNone(fl.parse_pull(1, None, {}))
        self.assertIsNone(fl.parse_pull(1, "not front matter", {}))

    def test_closed_time_from_close_event(self):
        pull = fl.parse_pull(3, pull_md("x", "closed", "bob", "2026-09-01T00:00:00Z"),
                             {"0001-close.md": event_md("close", "bob", "2026-10-03T00:00:00Z")})
        self.assertEqual(fl.month_of(pull["closed"]), "2026-10")

    def test_attribution_touched_folders_then_title(self):
        patch_text = ("diff --git a/blt-pool/src/x.py b/blt-pool/src/x.py\n"
                      "diff --git a/README.md b/README.md\n"
                      "diff --git a/.forkmesh/blt-leaf--ci.yml b/.forkmesh/blt-leaf--ci.yml\n")
        self.assertEqual(fl.pull_projects("blt-cron: x", patch_text), ["blt-leaf", "blt-pool"])
        self.assertEqual(fl.pull_projects("[blt-cron] tweak", ""), ["blt-cron"])
        self.assertEqual(fl.pull_projects("my-gsoc-tool: x", ""), ["my-gsoc-tool"])
        self.assertEqual(fl.pull_projects("CI: skip things", ""), [])
        self.assertEqual(fl.pull_projects("README only", "diff --git a/README.md b/README.md\n"), [])

    def test_bots(self):
        for name in ("", "forkmesh", "owasp-blt-actions", "dependabot[bot]", "release-bot", "CodeRabbitAI"):
            self.assertTrue(fl.is_bot(name), name)
        self.assertFalse(fl.is_bot("bob"))

    def test_counted_comments(self):
        self.assertTrue(fl.is_counted_comment("Looks good"))
        self.assertFalse(fl.is_counted_comment("/assign"))
        self.assertFalse(fl.is_counted_comment("@coderabbitai review"))
        self.assertFalse(fl.is_counted_comment("   "))


class TestContributions(unittest.TestCase):
    def setUp(self):
        self.roster = fl.compact_roster(ROSTER)

    def _pull(self, status="open", author="alice-forge", merged=None, events=()):
        files = {f"{i:04d}-{e[0]}.md": event_md(*e) for i, e in enumerate(events, start=1)}
        return fl.parse_pull(5, pull_md("blt-pool: x", status, author, "2026-10-01T00:00:00Z", merged=merged), files)

    def test_open_pull_maps_forge_login_to_github_login(self):
        c = fl.contributions(self._pull(), self.roster)
        self.assertEqual(c, {"open|Alice": 1, "2026-10|Alice|opened_prs": 1})

    def test_merged_pull(self):
        c = fl.contributions(self._pull("merged", merged="2026-11-01T00:00:00Z"), self.roster)
        self.assertEqual(c, {"2026-10|Alice|opened_prs": 1, "2026-11|Alice|merged_prs": 1})

    def test_closed_unmerged_pull(self):
        c = fl.contributions(self._pull("closed"), self.roster)
        self.assertEqual(c["2026-10|Alice|closed_prs"], 1)
        self.assertNotIn("open|Alice", c)

    def test_review_credits_first_two_other_humans_per_month(self):
        events = [
            ("review", "alice-forge", "2026-10-02T00:00:00Z", "self", "approved"),  # own PR: no credit
            ("review", "bob", "2026-10-02T01:00:00Z", "ok", "approved"),
            ("review", "bob", "2026-10-02T02:00:00Z", "again", "commented"),          # same reviewer
            ("review", "carol", "2026-10-03T00:00:00Z", "ok", "changes_requested"),
            ("review", "dave", "2026-10-04T00:00:00Z", "late", "approved"),           # third: no credit
            ("review", "dave", "2026-11-01T00:00:00Z", "next month", "approved"),     # new month
            ("review", "dependabot[bot]", "2026-10-05T00:00:00Z", "bot", "approved"),
        ]
        c = fl.contributions(self._pull(events=events), self.roster)
        reviews = {k: v for k, v in c.items() if k.endswith("|reviews")}
        self.assertEqual(reviews, {"2026-10|bob|reviews": 1, "2026-10|carol|reviews": 1, "2026-11|dave|reviews": 1})

    def test_comments(self):
        events = [
            ("comment", "bob", "2026-10-02T00:00:00Z", "nice"),
            ("line-comment", "bob", "2026-10-02T00:00:01Z", "nit"),
            ("comment", "bob", "2026-10-02T00:00:02Z", "/assign"),
            ("comment", "carol", "2026-10-02T00:00:03Z", "@coderabbitai summary"),
            ("comment", "forkmesh", "2026-10-02T00:00:04Z", "bot"),
            ("comment", "alice-forge", "2026-10-02T00:00:05Z", "thanks"),
        ]
        c = fl.contributions(self._pull(events=events), self.roster)
        self.assertEqual(c["2026-10|bob|comments"], 2)
        self.assertEqual(c["2026-10|Alice|comments"], 1)
        self.assertNotIn("2026-10|carol|comments", c)
        self.assertNotIn("2026-10|forkmesh|comments", c)

    def test_bot_author_gets_nothing_but_human_reviews_count(self):
        events = [("review", "bob", "2026-10-02T00:00:00Z", "ok", "approved")]
        c = fl.contributions(self._pull(author="dependabot[bot]", events=events), self.roster)
        self.assertEqual(c, {"2026-10|bob|reviews": 1})

    def test_deleted_and_missing(self):
        self.assertEqual(fl.contributions(self._pull("deleted"), self.roster), {})
        self.assertEqual(fl.contributions(None, self.roster), {})

    def test_diff_and_statements(self):
        old = {"open|bob": 1, "2026-10|bob|opened_prs": 1}
        new = {"2026-10|bob|opened_prs": 1, "2026-10|bob|merged_prs": 1}
        delta = fl.diff(old, new)
        self.assertEqual(delta, {"open|bob": -1, "2026-10|bob|merged_prs": 1})
        statements = fl.delta_statements(ORG, delta, NOW)
        self.assertEqual(len(statements), 2)  # one monthly upsert, one open-PR upsert


class TestIdentities(unittest.TestCase):
    def test_roster(self):
        roster = fl.compact_roster(ROSTER)
        self.assertEqual(fl.resolve(roster, "alice-forge"), "Alice")
        self.assertEqual(fl.resolve(roster, "ALICE"), "Alice")
        self.assertEqual(fl.resolve(roster, "stranger"), "stranger")
        self.assertNotIn("dependabot[bot]", roster)
        self.assertEqual(fl.compact_roster(None), {})
        self.assertEqual(fl.compact_roster({"contributors": "bad"}), {})

    def test_person(self):
        roster = fl.compact_roster(ROSTER)
        alice = fl.person("Alice", roster, {"alice"})
        self.assertEqual(alice["name"], "Alice Example")
        self.assertEqual(alice["avatar_url"], f"{API}/raw?path=.forkmesh/contributors/alice.png")
        self.assertEqual(alice["profile_url"], "https://git.owaspblt.org/@Alice")
        forge_only = fl.person("newbie", roster, {"newbie"})
        self.assertEqual(forge_only["avatar_url"], "https://git.owaspblt.org/api/accounts/newbie/avatar")
        github_only = fl.person("OldGitHubUser", roster, set())
        self.assertIn("avatars.githubusercontent.com/OldGitHubUser", github_only["avatar_url"])
        self.assertEqual(github_only["profile_url"], "https://github.com/OldGitHubUser")

    def test_merge_rows_combines_case_variants(self):
        stats = fl.merge_rows(
            [{"user_login": "Alice", "merged_prs": 2, "reviews": 1},
             {"user_login": "alice", "opened_prs": 1, "merged_prs": 1, "comments": 3}],
            [{"user_login": "ALICE", "open_prs": 1}],
            fl.compact_roster(ROSTER),
        )
        self.assertEqual(list(stats), ["Alice"])
        s = stats["Alice"]
        self.assertEqual((s["openPrs"], s["openedPrs"], s["mergedPrs"], s["reviews"], s["comments"]), (1, 1, 3, 1, 3))
        self.assertEqual(s["total"], 1 + 30 + 5 + 6)


# ---------------------------------------------------------------------------
# Incremental sync against D1
# ---------------------------------------------------------------------------

class TestSync(unittest.TestCase):
    def setUp(self):
        self.db = FakeD1()
        self.store = _worker._D1Store(self.db)
        self.forge = FakeForge(ROSTER)

    def sync(self, now=NOW, max_pulls=8, max_requests=40):
        client = fl.ForgeClient(self.forge, max_requests=max_requests)
        calls = len(self.forge.calls)
        summary = run(fl.sync(client, self.store, ORG, now=now, max_pulls=max_pulls))
        summary["gets"] = len(self.forge.calls) - calls
        return summary

    def monthly(self):
        return {(r["month_key"], r["user_login"]): r for r in
                self.db.rows("SELECT * FROM leaderboard_monthly_stats WHERE org = ?", (ORG,))}

    def open_prs(self):
        return {r["user_login"]: r["open_prs"] for r in self.db.rows("SELECT * FROM leaderboard_open_prs")}

    def test_empty_ledger(self):
        first = self.sync()
        self.assertEqual(first["ledger"], "missing")
        self.assertEqual(first["gets"], 2)          # roster + ledger tree
        self.assertEqual(first["statements"], 1)    # the cursor (roster) row
        writes = self.db.writes
        second = self.sync(now=NOW + 1200)
        self.assertEqual(second["gets"], 1)         # roster is daily; just the ledger tree
        self.assertEqual(second["statements"], 0)
        self.assertEqual(self.db.writes, writes)
        self.assertEqual(self.monthly(), {})

    def test_roster_unreachable_still_reads_ledger(self):
        self.forge.roster = None
        summary = self.sync()
        self.assertEqual(summary["ledger"], "missing")

    def test_ledger_appears_and_idle_runs_cost_nothing(self):
        self.sync()  # empty
        self.forge.set_pull(1, {"pull.md": pull_md("blt-pool: a", "open", "alice-forge", "2026-10-01T00:00:00Z"),
                                "0001-review.md": event_md("review", "bob", "2026-10-02T00:00:00Z", state="approved"),
                                "0002-comment.md": event_md("comment", "bob", "2026-10-02T01:00:00Z")})
        self.forge.set_pull(2, {"pull.md": pull_md("[blt-leaf] b", "merged", "bob", "2026-10-03T00:00:00Z",
                                                   merged="2026-10-04T00:00:00Z")})
        summary = self.sync(now=NOW + 1200)
        self.assertEqual(summary["ledger"], "ok")
        self.assertEqual(summary["pulls_read"], 2)
        self.assertEqual(summary["pending"], 0)
        m = self.monthly()
        self.assertEqual(m[("2026-10", "Alice")]["opened_prs"], 1)
        self.assertEqual(m[("2026-10", "bob")]["reviews"], 1)
        self.assertEqual(m[("2026-10", "bob")]["comments"], 1)
        self.assertEqual(m[("2026-10", "bob")]["merged_prs"], 1)
        self.assertEqual(self.open_prs(), {"Alice": 1})
        pulls = {r["pr_number"]: r for r in self.db.rows("SELECT * FROM leaderboard_forge_pulls")}
        self.assertEqual(pulls[1]["projects"], "blt-pool")
        self.assertEqual(pulls[2]["projects"], "blt-leaf")
        self.assertEqual(pulls[1]["author_login"], "Alice")

        writes = self.db.writes
        idle = self.sync(now=NOW + 2400)
        self.assertEqual(idle["gets"], 1)
        self.assertEqual(idle["statements"], 0)
        self.assertEqual(self.db.writes, writes)

    def test_changed_pull_applies_only_the_difference(self):
        self.forge.set_pull(1, {"pull.md": pull_md("blt-pool: a", "open", "bob", "2026-10-01T00:00:00Z")}, oid="a")
        self.sync()
        self.forge.commit = "c2"
        self.forge.set_pull(1, {"pull.md": pull_md("blt-pool: a", "merged", "bob", "2026-10-01T00:00:00Z",
                                                   merged="2026-10-05T00:00:00Z"),
                                "0001-comment.md": event_md("comment", "carol", "2026-10-05T00:00:00Z")}, oid="b")
        summary = self.sync(now=NOW + 1200)
        self.assertEqual(summary["pulls_read"], 1)
        m = self.monthly()
        self.assertEqual(m[("2026-10", "bob")]["opened_prs"], 1)  # not counted twice
        self.assertEqual(m[("2026-10", "bob")]["merged_prs"], 1)
        self.assertEqual(m[("2026-10", "carol")]["comments"], 1)
        self.assertEqual(self.open_prs(), {"bob": 0})
        # Same commit again: nothing is re-read or re-counted.
        self.forge.commit = "c2"
        self.sync(now=NOW + 2400)
        self.assertEqual(self.monthly()[("2026-10", "bob")]["merged_prs"], 1)

    def test_unchanged_folders_are_not_reread_when_the_ledger_moves(self):
        self.forge.set_pull(1, {"pull.md": pull_md("x", "open", "bob", "2026-10-01T00:00:00Z")}, oid="a")
        self.sync()
        self.forge.commit = "c2"
        self.forge.set_pull(2, {"pull.md": pull_md("y", "open", "carol", "2026-10-02T00:00:00Z")}, oid="z")
        summary = self.sync(now=NOW + 1200)
        self.assertEqual(summary["pulls_read"], 1)
        self.assertEqual(summary["gets"], 3)  # ledger tree + pull 2's listing + its blobs

    def test_cursor_resumes_when_a_run_stops_early(self):
        for n in (1, 2, 3):
            self.forge.set_pull(n, {"pull.md": pull_md("x", "open", f"user{n}", "2026-10-01T00:00:00Z")})
        first = self.sync(max_pulls=2)
        self.assertEqual((first["pulls_read"], first["pending"]), (2, 1))
        cursor = self.db.rows("SELECT ledger_commit FROM leaderboard_forge_cursor")[0]
        self.assertEqual(cursor["ledger_commit"], "")  # not complete: next run lists again
        second = self.sync(now=NOW + 1200, max_pulls=2)
        self.assertEqual((second["pulls_read"], second["pending"]), (1, 0))
        self.assertEqual(self.db.rows("SELECT ledger_commit FROM leaderboard_forge_cursor")[0]["ledger_commit"], "c1")
        self.assertEqual(self.open_prs(), {"user1": 1, "user2": 1, "user3": 1})

    def test_request_budget_stops_cleanly(self):
        for n in range(1, 6):
            self.forge.set_pull(n, {"pull.md": pull_md("x", "open", f"user{n}", "2026-10-01T00:00:00Z")})
        summary = self.sync(max_requests=6)  # roster + tree + 2 pulls x 2 GETs
        self.assertEqual(summary["pulls_read"], 2)
        self.assertEqual(summary["pending"], 3)
        self.assertEqual(len(self.open_prs()), 2)

    def test_removed_pull_reverses_its_contributions(self):
        self.forge.set_pull(1, {"pull.md": pull_md("x", "merged", "bob", "2026-10-01T00:00:00Z",
                                                   merged="2026-10-02T00:00:00Z")})
        self.forge.set_pull(2, {"pull.md": pull_md("y", "open", "carol", "2026-10-01T00:00:00Z")})
        self.sync()
        del self.forge.ledger["1"]
        self.forge.commit = "c2"
        summary = self.sync(now=NOW + 1200)
        self.assertEqual(summary["pulls_removed"], 1)
        self.assertEqual(self.monthly()[("2026-10", "bob")]["merged_prs"], 0)
        self.assertEqual(self.db.rows("SELECT pr_number FROM leaderboard_forge_pulls"), [{"pr_number": 2}])

    def test_pull_refs_not_yet_in_the_ledger(self):
        self.forge.set_pull(4, {"pull.md": pull_md("x", "open", "bob", "2026-10-01T00:00:00Z")})
        self.forge.set_pull(5, {"pull.md": pull_md("y", "open", "carol", "2026-10-01T00:00:00Z")})
        self.forge.unlisted = {"5"}
        self.forge.pull_refs = {"5": "forkmesh/pull/5"}
        self.sync()
        self.assertEqual(self.open_prs(), {"bob": 1, "carol": 1})
        oids = {r["pr_number"]: r["oid"] for r in self.db.rows("SELECT pr_number, oid FROM leaderboard_forge_pulls")}
        self.assertEqual(oids[5], "ref:forkmesh/pull/5")

    def test_branch_pull_without_patch_uses_compare(self):
        self.forge.set_pull(9, {"pull.md": pull_md("No prefix", "open", "bob", "2026-10-01T00:00:00Z",
                                                   extra="derive: branch\nmergeBase: aaa\nmergeHead: bbb\n")})
        self.sync()
        self.assertEqual(self.db.rows("SELECT projects FROM leaderboard_forge_pulls")[0]["projects"], "blt-leaf")

    def test_github_history_is_kept_and_combined(self):
        self.db.conn.execute(
            "INSERT INTO leaderboard_monthly_stats (org, month_key, user_login, merged_prs, closed_prs, reviews, comments, updated_at) "
            "VALUES (?, '2026-10', 'Alice', 3, 0, 2, 4, 1)", (ORG,))
        self.db.conn.execute("INSERT INTO leaderboard_open_prs (org, user_login, open_prs, updated_at) VALUES (?, 'Alice', 1, 1)", (ORG,))
        self.db.conn.commit()
        self.forge.set_pull(1, {"pull.md": pull_md("x", "merged", "alice-forge", "2026-10-01T00:00:00Z",
                                                   merged="2026-10-02T00:00:00Z")})
        self.sync()
        row = self.monthly()[("2026-10", "Alice")]
        self.assertEqual((row["merged_prs"], row["reviews"], row["comments"], row["opened_prs"]), (4, 2, 4, 1))
        self.assertEqual(self.open_prs(), {"Alice": 1})

    def test_forge_error_does_not_write(self):
        async def broken(url):
            return 503, None
        client = fl.ForgeClient(broken)
        with self.assertRaises(fl.ForgeError):
            run(fl.sync(client, self.store, ORG, now=NOW))
        self.assertEqual(self.db.rows("SELECT * FROM leaderboard_forge_cursor"), [])


# ---------------------------------------------------------------------------
# Worker routes and cron task
# ---------------------------------------------------------------------------

class TestWorkerLeaderboard(unittest.TestCase):
    def setUp(self):
        _worker._LEADERBOARD_MEMO.clear()
        self.db = FakeD1()
        self.env = types.SimpleNamespace(LEADERBOARD_DB=self.db, GITHUB_ORG=ORG)
        self.forge = FakeForge(ROSTER)
        self.quiet = types.SimpleNamespace(error=lambda *a: None, log=lambda *a: None)

    def _sync(self):
        with patch.object(_worker, "console", new=self.quiet):
            return run(_worker._run_forge_leaderboard_sync(self.env, get_json=self.forge, now=NOW))

    def _get(self, url):
        req = types.SimpleNamespace(method="GET", url=url, headers=_worker.Headers.new({}.items()))

        async def inner():
            with patch.object(_worker, "console", new=self.quiet):
                return await _worker.on_fetch(req, self.env)
        return run(inner())

    def test_empty_everything(self):
        self.assertEqual(self._sync()["ledger"], "missing")
        resp = self._get("https://pool.owaspblt.org/api/leaderboard?month=2026-10")
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertEqual(data["sorted"], [])
        self.assertEqual(data["users"], {})
        self.assertEqual(data["recent_pulls"], [])
        html = self._get("https://pool.owaspblt.org/leaderboard?month=2026-10").body
        self.assertIn("No pull request activity recorded for October 2026", html)
        self.assertIn("https://git.owaspblt.org/BLT/pulls", html)

    def test_api_shape_and_page(self):
        self.db.conn.execute(
            "INSERT INTO leaderboard_monthly_stats (org, month_key, user_login, merged_prs, closed_prs, reviews, comments, updated_at) "
            "VALUES (?, '2026-10', 'ghost', 1, 0, 0, 0, 1)", (ORG,))
        self.db.conn.commit()
        self.forge.set_pull(12, {"pull.md": pull_md("blt-pool: <b>bold</b>", "merged", "alice-forge",
                                                    "2026-10-01T00:00:00Z", merged="2026-10-02T00:00:00Z"),
                                 "0001-review.md": event_md("review", "bob", "2026-10-01T05:00:00Z", state="approved")})
        self._sync()
        data = json.loads(self._get("https://pool.owaspblt.org/api/leaderboard?month=2026-10").body)
        for key in ("users", "sorted", "start_timestamp", "end_timestamp", "month", "recent_pulls"):
            self.assertIn(key, data)
        first = data["sorted"][0]
        self.assertEqual(first["login"], "Alice")
        self.assertEqual(first["name"], "Alice Example")
        self.assertEqual(first["total"], 10)
        self.assertEqual(data["users"]["bob"]["reviews"], 1)
        self.assertEqual(data["recent_pulls"][0]["url"], "https://git.owaspblt.org/BLT/pulls/12")
        self.assertEqual(data["recent_pulls"][0]["projects"], ["blt-pool"])
        ghost = next(u for u in data["sorted"] if u["login"] == "ghost")
        self.assertIn("github.com/ghost", ghost["profile_url"])
        html = self._get("https://pool.owaspblt.org/leaderboard?month=2026-10").body
        self.assertIn("Alice Example", html)
        self.assertIn('href="https://git.owaspblt.org/BLT/pulls/12"', html)
        self.assertIn("&lt;b&gt;bold&lt;/b&gt;", html)
        self.assertNotIn("<b>bold</b>", html)

    def test_responses_are_cached_per_isolate(self):
        self._get("https://pool.owaspblt.org/api/leaderboard?month=2026-10")
        reads = self.db.reads
        self._get("https://pool.owaspblt.org/api/leaderboard?month=2026-10")
        self.assertEqual(self.db.reads, reads)

    def test_bad_month(self):
        self.assertEqual(self._get("https://pool.owaspblt.org/api/leaderboard?month=2026-13").status, 400)

    def test_cron_task_runs_forge_sync(self):
        sync = AsyncMock(return_value={"ok": True})
        stale = AsyncMock()
        with patch.object(_worker, "_run_forge_leaderboard_sync", new=sync), \
                patch.object(_worker, "_run_scheduled", new=stale):
            run(_worker.on_scheduled(_worker._CronEvent("6-59/20 * * * *", 1, "forge-leaderboard"), self.env))
            sync.assert_awaited_once()
            stale.assert_not_awaited()
            run(_worker.on_scheduled(_worker._CronEvent("0 */2 * * *", 1), self.env))
            stale.assert_awaited_once()

    def test_cron_dispatch_passes_the_task(self):
        env = types.SimpleNamespace(CRON_SECRET="s3cret")
        req = types.SimpleNamespace(
            method="POST", url="https://cron.internal/__scheduled",
            headers=_worker.Headers.new({"X-BLT-Cron-Secret": "s3cret"}.items()),
            text=AsyncMock(return_value=json.dumps({"cron": "x", "scheduledTime": 1, "task": "forge-leaderboard"})),
        )
        handler = AsyncMock()
        with patch.object(_worker, "on_scheduled", new=handler), patch.object(_worker, "console", new=self.quiet):
            resp = run(_worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        self.assertEqual(handler.await_args.args[0].task, "forge-leaderboard")


if __name__ == "__main__":
    unittest.main()
