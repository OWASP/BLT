"""Forge source: normalizer, poller cursor logic, and the scheduled run."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlparse

import pytest

from src.ingestion.forge_poller import (
    CURSOR_SOURCE,
    ForgeClient,
    ForgeConfig,
    poll,
    run_forge_poll,
)
from src.models.event import Event
from src.normalization.forge import (
    is_bot,
    normalize_forge_commit,
    normalize_forge_issue,
    normalize_forge_pull,
    parse_forge_time,
    subject_folders,
)
from src.pipeline.consumer import process_pipeline_event
from src.storage import CursorQueries, EventQueries


WEB = "https://git.owaspblt.org/BLT"
FOLDERS = frozenset({"blt-hackerhouse", "blt-cron", "blt-pool", "docs"})
NOW = datetime(2026, 10, 20, 1, 0, tzinfo=timezone.utc)
CONFIG = ForgeConfig(max_requests=40)


def ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def commit(sha: str, date: str, subject: str, author: str = "DonnieBLT", parents: str | None = None) -> dict:
    return {"hash": sha, "date": date, "subject": subject, "author": author, "parents": parents or f"{sha}p"}


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------

class TestNormalizer:
    def test_times_with_offsets_and_milliseconds_become_utc(self):
        assert parse_forge_time("2026-10-19T20:07:34-04:00") == datetime(2026, 10, 20, 0, 7, 34, tzinfo=timezone.utc)
        assert parse_forge_time(1792290689619) == datetime(2026, 10, 18, 2, 31, 29, tzinfo=timezone.utc)
        assert parse_forge_time("nonsense") is None
        assert parse_forge_time(None) is None

    def test_subject_prefix_names_folders(self):
        assert subject_folders("blt-pool: create tables", FOLDERS) == ["blt-pool"]
        assert subject_folders("blt-cron, blt-pool: wording", FOLDERS) == ["blt-cron", "blt-pool"]
        assert subject_folders("[docs] fix links", FOLDERS) == ["docs"]
        assert subject_folders("CI: tests accept real KV ids", FOLDERS) == []
        assert subject_folders("Eight projects: say Source code", FOLDERS) == []
        assert subject_folders("Import blt-pool history into blt-pool/", FOLDERS) == []

    def test_bots(self):
        bots = ForgeConfig().bots
        assert is_bot("owasp-blt-actions", bots)
        assert is_bot("forkmesh", bots)
        assert is_bot("renovate[bot]", bots)
        assert is_bot("", bots)
        assert not is_bot("DonnieBLT", bots)

    def test_commit(self):
        event = normalize_forge_commit(
            commit("abc123", "2026-10-19T20:07:34-04:00", "blt-pool: create the tables once"),
            web_url=WEB, folders=FOLDERS,
        )
        assert event.source == "forge"
        assert event.event_type == "commit_pushed"
        assert event.actor_id == event.actor_name == "DonnieBLT"
        assert event.repository == "blt-pool"
        assert event.timestamp == datetime(2026, 10, 20, 0, 7, 34)
        assert event.metadata["url"] == f"{WEB}/commit/abc123"
        assert event.metadata["commit_sha"] == "abc123"
        assert event.idempotency_key == "forge:commit_pushed:abc123"

    def test_commits_in_the_same_second_by_the_same_author_stay_distinct(self):
        a = normalize_forge_commit(commit("a1", "2026-10-17T15:11:00-04:00", "Update logos"), web_url=WEB)
        b = normalize_forge_commit(commit("b2", "2026-10-17T15:11:00-04:00", "Update logos"), web_url=WEB)
        assert a.repository == "BLT"
        assert a.idempotency_key != b.idempotency_key

    def test_issue_events_after_the_cursor(self):
        raw = {
            "number": 7, "title": "blt-cron: retry failed jobs", "authorName": "alice",
            "createdAt": ms("2026-10-18T00:00:00Z"), "labels": [],
            "events": [
                {"type": "open", "id": "open-1", "ts": ms("2026-10-18T00:00:00Z"), "authorName": "alice"},
                {"type": "vote", "id": "vote-1", "ts": ms("2026-10-18T01:00:00Z"), "authorName": "bob"},
                {"type": "comment", "id": "c-1", "ts": ms("2026-10-18T02:00:00Z"), "authorName": "bob", "body": "+1 " * 200},
                {"type": "close", "id": "close-1", "ts": ms("2026-10-19T00:00:00Z"), "authorName": "alice"},
            ],
        }
        events, newest = normalize_forge_issue(raw, web_url=WEB, folders=FOLDERS)
        assert [e.event_type for e in events] == ["issue_opened", "note_added", "issue_closed"]
        assert events[0].repository == "blt-cron"
        assert events[0].metadata["url"] == f"{WEB}/issues/7"
        assert events[1].actor_name == "bob"
        assert len(events[1].metadata["body"]) <= 280
        assert newest == ms("2026-10-19T00:00:00Z")
        assert len({e.idempotency_key for e in events}) == 3

        later, _ = normalize_forge_issue(raw, web_url=WEB, after_ms=ms("2026-10-18T02:00:00Z"))
        assert [e.event_type for e in later] == ["issue_closed"]

    def test_issue_label_wins_over_title(self):
        raw = {"number": 2, "title": "docs: x", "authorName": "a", "createdAt": ms("2026-10-19T00:00:00Z"),
               "labels": [{"name": "project:blt-pool"}], "events": []}
        events, _ = normalize_forge_issue(raw, web_url=WEB, folders=FOLDERS)
        assert [e.event_type for e in events] == ["issue_opened"]  # synthesized from createdAt
        assert events[0].repository == "blt-pool"

    def test_pull_opened_merged_and_reviewed(self):
        pull_md = (
            "---\ntitle: blt-hackerhouse: forge feed\nstatus: merged\n"
            f"ts: {ms('2026-10-18T00:00:00Z')}\nauthorName: alice\n"
            f"mergedAt: {ms('2026-10-19T00:00:00Z')}\nmergedByName: DonnieBLT\n---\nbody\n"
        )
        files = {
            ".forkmesh/pulls/3/0001-review.md": f"---\ntype: review\nstate: approved\nid: r1\nts: {ms('2026-10-18T12:00:00Z')}\nauthorName: bob\n---\nLGTM",
            ".forkmesh/pulls/3/0002-status.md": f"---\ntype: status\nts: {ms('2026-10-19T00:00:00Z')}\nauthorName: DonnieBLT\n---\n",
        }
        events, seen = normalize_forge_pull(3, pull_md, files, web_url=WEB, previous=None, folders=FOLDERS)
        assert sorted(e.event_type for e in events) == ["mr_merged", "mr_opened", "note_added"]
        merged = next(e for e in events if e.event_type == "mr_merged")
        assert merged.actor_name == "DonnieBLT"
        assert merged.repository == "blt-hackerhouse"
        assert merged.metadata["url"] == f"{WEB}/pulls/3"
        note = next(e for e in events if e.event_type == "note_added")
        assert note.metadata["review_state"] == "approved"
        assert seen == {"ts": ms("2026-10-19T00:00:00Z"), "status": "merged"}

        again, _ = normalize_forge_pull(3, pull_md, files, web_url=WEB, previous=seen)
        assert again == []

    def test_unreadable_pull(self):
        assert normalize_forge_pull(1, None, {}, web_url=WEB, previous=None) == ([], None)


# ---------------------------------------------------------------------------
# Poller and cursor
# ---------------------------------------------------------------------------

class FakeForge:
    """Answers the forge read API from dicts and records each request."""

    def __init__(self, history: list[dict], issues: dict[int, dict] | None = None, pulls: dict | None = None):
        self.history = history
        self.issues = issues or {}
        self.pulls = pulls  # None: no ledger branch (404)
        self.calls: list[tuple[str, dict]] = []

    def oid(self, value) -> str:
        return str(abs(hash(json.dumps(value, sort_keys=True))))

    async def __call__(self, url: str):
        parsed = urlparse(url)
        op = parsed.path.rsplit("/", 1)[-1]
        params = parse_qsl(parsed.query, keep_blank_values=True)
        query = dict(params)
        self.calls.append((op, query))
        if op == "history":
            ref = query.get("ref")
            start = 0 if ref == "main" else next(
                (i for i, c in enumerate(self.history) if c["hash"] == ref), len(self.history))
            return 200, {"commits": self.history[start:start + 2]}  # pages of 2
        if op == "tree":
            path = query.get("path")
            if path == "":
                return 200, {"entries": [{"name": f, "type": "tree", "oid": "x"} for f in FOLDERS]
                             + [{"name": ".forkmesh", "type": "tree", "oid": "y"}, {"name": "README.md", "type": "blob"}]}
            if path == ".forkmesh/issues":
                return 200, {"entries": [{"name": "open", "type": "tree", "oid": self.oid(self.issues)}]}
            if path == ".forkmesh/issues/open":
                return 200, {"entries": [{"name": str(n), "type": "tree", "oid": self.oid(r)} for n, r in self.issues.items()]}
            if path == ".forkmesh/pulls":
                if self.pulls is None:
                    return 404, None
                return 200, {"commit": self.oid(self.pulls), "entries": [
                    {"name": str(n), "type": "tree", "oid": self.oid(p)} for n, p in self.pulls.items()]}
            if path.startswith(".forkmesh/pulls/"):
                number = int(path.rsplit("/", 1)[-1])
                return 200, {"entries": [{"name": name.rsplit("/", 1)[-1], "type": "blob"} for name in self.pulls[number]]}
        if op == "blobs":
            blobs = {}
            for key, value in params:
                if key != "path":
                    continue
                if value.startswith(".forkmesh/issues/"):
                    number = int(value.split("/")[3])
                    blobs[value] = {"content": json.dumps(self.issues[number]), "encoding": "utf8"}
                elif value.startswith(".forkmesh/pulls/"):
                    number = int(value.split("/")[2])
                    blobs[value] = {"content": self.pulls[number][value.rsplit("/", 1)[-1]], "encoding": "utf8"}
            return 200, {"blobs": blobs}
        return 404, None

    def ops(self) -> list[str]:
        return [op for op, _ in self.calls]


HISTORY = [
    commit("c5", "2026-10-19T23:00:00Z", "README: refresh generated sections", author="owasp-blt-actions"),
    commit("c4", "2026-10-19T20:00:00-04:00", "blt-pool: create tables once"),
    commit("c3", "2026-10-19T12:00:00Z", "Merge branch x", parents="c2 zz"),
    commit("c2", "2026-10-18T12:00:00Z", "docs: retirement plan", author="Claude Opus 5.5"),
    commit("c1", "2026-09-01T00:00:00Z", "blt-cron: old work"),
    commit("c0", "2026-08-01T00:00:00Z", "older still", parents=""),
]
# Pages follow the last commit's first parent; make the fake's parents point at the next commit.
for _i, _c in enumerate(HISTORY[:-1]):
    if " " not in _c["parents"]:
        _c["parents"] = HISTORY[_i + 1]["hash"]
HISTORY[2]["parents"] = "c2 zz"

ISSUE = {
    "number": 1, "title": "deploy the new website", "authorName": "donnieblt",
    "createdAt": ms("2026-10-18T02:31:29Z"),
    "events": [{"type": "open", "id": "open-web-1", "ts": ms("2026-10-18T02:31:29Z"), "authorName": "donnieblt"}],
}


class TestPoll:
    async def test_first_run_backfills_the_window_and_skips_bots_and_merges(self):
        forge = FakeForge(HISTORY, {1: ISSUE})
        result = await poll(ForgeClient(forge, CONFIG), None, CONFIG, NOW)
        kinds = [(e.event_type, e.actor_name) for e in result.events]
        assert kinds == [
            ("issue_opened", "donnieblt"),
            ("commit_pushed", "Claude Opus 5.5"),
            ("commit_pushed", "DonnieBLT"),
        ]
        assert result.skipped_bots == 1
        assert result.events[-1].repository == "blt-pool"
        state = result.state
        assert state["commit_sha"] == "c5"
        assert state["issues_head"] == "c5"
        assert state["issues"]["1"][1] == ms("2026-10-18T02:31:29Z")
        assert sorted(state["folders"]) == sorted(FOLDERS)
        # c1 is older than 7 days: the page holding it ends the walk
        assert forge.ops().count("history") == 3
        assert result.requests == len(forge.calls) <= CONFIG.max_requests

    async def test_idle_run_makes_two_requests_and_keeps_the_state(self):
        forge = FakeForge(HISTORY, {1: ISSUE})
        first = await poll(ForgeClient(forge, CONFIG), None, CONFIG, NOW)
        forge.calls.clear()
        again = await poll(ForgeClient(forge, CONFIG), first.state, CONFIG, NOW)
        assert again.events == []
        assert again.state == first.state
        assert forge.ops() == ["history", "tree"]  # main's head, then the pull ledger (404)

    async def test_new_commits_and_issue_events_only(self):
        forge = FakeForge(HISTORY, {1: ISSUE})
        first = await poll(ForgeClient(forge, CONFIG), None, CONFIG, NOW)
        forge.history = [commit("c7", "2026-10-20T00:30:00Z", "blt-cron: add hackerhouse", parents="c6"),
                         commit("c6", "2026-10-20T00:20:00Z", "issue #1: comment", author="forkmesh", parents="c5")] + HISTORY
        forge.issues = {1: {**ISSUE, "events": ISSUE["events"] + [
            {"type": "comment", "id": "c-9", "ts": ms("2026-10-20T00:20:00Z"), "authorName": "bob", "body": "on it"}]}}
        forge.calls.clear()
        second = await poll(ForgeClient(forge, CONFIG), first.state, CONFIG, NOW)
        assert [(e.event_type, e.actor_name) for e in second.events] == [
            ("note_added", "bob"), ("commit_pushed", "DonnieBLT")]
        assert second.events[-1].repository == "blt-cron"
        assert second.state["commit_sha"] == "c7"
        # history page (c7, c6), next page reaches c5; issue root + open tree + one blobs read; pulls
        assert forge.ops() == ["history", "history", "tree", "tree", "blobs", "tree"]

    async def test_pulls_from_the_ledger(self):
        pulls = {4: {
            "pull.md": f"---\ntitle: blt-pool: faster\nstatus: open\nts: {ms('2026-10-19T00:00:00Z')}\nauthorName: carol\n---\n",
            "0001-comment.md": f"---\ntype: comment\nid: k1\nts: {ms('2026-10-19T01:00:00Z')}\nauthorName: dave\n---\nnice",
            "changes.patch": "diff --git a/x b/x",
        }}
        forge = FakeForge(HISTORY, {1: ISSUE}, pulls)
        first = await poll(ForgeClient(forge, CONFIG), None, CONFIG, NOW)
        pull_events = [(e.event_type, e.actor_name) for e in first.events if "pull_number" in e.metadata]
        assert pull_events == [("mr_opened", "carol"), ("note_added", "dave")]
        assert first.state["pulls"]["4"]["status"] == "open"
        blob_paths = [q for op, q in forge.calls if op == "blobs"][-1]
        assert "changes.patch" not in json.dumps(blob_paths)

        pulls[4]["pull.md"] = pulls[4]["pull.md"].replace("status: open", f"status: merged\nmergedAt: {ms('2026-10-19T06:00:00Z')}")
        second = await poll(ForgeClient(forge, CONFIG), first.state, CONFIG, NOW)
        assert [(e.event_type, e.actor_name) for e in second.events] == [("mr_merged", "carol")]

    async def test_request_budget_stops_and_resumes(self):
        forge = FakeForge(HISTORY, {1: ISSUE})
        tight = ForgeConfig(max_requests=4)  # folders + 3 history pages, then out
        partial = await poll(ForgeClient(forge, tight), None, tight, NOW)
        assert partial.complete is False
        assert partial.requests == 4
        assert partial.state["commit_sha"] == "c5"
        assert "issues_head" not in partial.state
        assert [e.metadata.get("commit_sha") for e in partial.events] == ["c2", "c4"]
        rest = await poll(ForgeClient(forge, CONFIG), partial.state, CONFIG, NOW)
        assert rest.complete is True
        assert rest.state["issues_head"] == "c5"

    async def test_event_cap_keeps_the_newest(self):
        forge = FakeForge(HISTORY, {1: ISSUE})
        capped = ForgeConfig(max_events=1)
        result = await poll(ForgeClient(forge, capped), None, capped, NOW)
        assert [e.metadata.get("commit_sha") for e in result.events] == ["c4"]


# ---------------------------------------------------------------------------
# Scheduled run: cursor in D1, events through the queue consumer
# ---------------------------------------------------------------------------

class FakeQueue:
    def __init__(self):
        self.batches: list[list[dict]] = []

    async def sendBatch(self, messages):
        self.batches.append(list(messages))


class FakeEnv:
    def __init__(self, db):
        self.HH_DB = db
        self.PIPELINE_QUEUE = FakeQueue()


class TestRun:
    async def test_run_saves_the_cursor_and_events_reach_the_store(self, db):
        env = FakeEnv(db)
        forge = FakeForge(HISTORY, {1: ISSUE})
        summary = await run_forge_poll(env, get_json=forge, now=NOW, config=CONFIG)
        assert summary["ok"] is True and summary["events"] == 3
        stored = await CursorQueries(db).get_state(CURSOR_SOURCE)
        assert stored["state"]["commit_sha"] == "c5"
        assert stored["last_seen_id"] == 3

        messages = [m for batch in env.PIPELINE_QUEUE.batches for m in batch]
        for message in messages:
            await process_pipeline_event(json.loads(message["body"]), db, object(), record_health=False)
        for message in messages:  # a re-delivery is a no-op
            await process_pipeline_event(json.loads(message["body"]), db, object(), record_health=False)
        assert await EventQueries(db).count() == 3
        events, total = await EventQueries(db).list_activity(page=1, per_page=10)
        assert total == 3
        assert {e.source for e in events} == {"forge"}

    async def test_idle_run_writes_nothing(self, db):
        env = FakeEnv(db)
        forge = FakeForge(HISTORY, {1: ISSUE})
        await run_forge_poll(env, get_json=forge, now=NOW, config=CONFIG)
        before = await CursorQueries(db).get_state(CURSOR_SOURCE)

        writes = []
        original = db.prepare

        def spy(sql):
            if sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                writes.append(sql)
            return original(sql)

        db.prepare = spy
        summary = await run_forge_poll(env, get_json=forge, now=NOW, config=CONFIG)
        assert summary["events"] == 0
        assert writes == []
        assert await CursorQueries(db).get_state(CURSOR_SOURCE) == before

    async def test_failure_is_recorded_once(self, db):
        env = FakeEnv(db)

        async def broken(url):
            return 503, None

        first = await run_forge_poll(env, get_json=broken, now=NOW, config=CONFIG)
        assert first["ok"] is False
        stored = await CursorQueries(db).get_state(CURSOR_SOURCE)
        assert "503" in stored["state"]["last_error"]

        forge = FakeForge(HISTORY, {1: ISSUE})
        await run_forge_poll(env, get_json=forge, now=NOW, config=CONFIG)
        stored = await CursorQueries(db).get_state(CURSOR_SOURCE)
        assert "last_error" not in stored["state"]
        assert stored["state"]["commit_sha"] == "c5"


def test_forge_event_types_are_validated():
    with pytest.raises(ValueError):
        Event(source="forge", event_type="bug_bounty_submitted", actor_id="a", actor_name="a")
    Event(source="forge", event_type="commit_pushed", actor_id="a", actor_name="a")
