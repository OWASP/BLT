"""Forge poller: BLT monorepo activity from git.owaspblt.org.

Runs from ``scheduled()`` (or blt-cron's ``POST /__scheduled``). Each run:

1. ``history?ref=main``: new commits since the cursor's sha (paged by parent,
   at most ``max_history_pages`` pages) become ``commit_pushed`` events;
2. only when main moved since the issue ledger was last read: the
   ``.forkmesh/issues`` tree, the ``open``/``closed`` sub-trees whose oid
   changed, and ``blobs`` (50 files a request) for the issue folders whose oid
   changed. New issue events (open, comment, close) become events;
3. the ``forkmesh/pulls`` ledger tree (404 means no pulls yet); for pull
   folders whose oid changed, their file list and files.

The cursor is one ``poll_cursors`` row (``source = 'forge'``) whose
``metadata`` JSON holds the last commit, the ledger oids and the folder list.
It is written only when it changed, so an idle run costs one D1 read and no
writes. Events are sent to the pipeline queue (``sendBatch``, 100 a call),
whose consumer dedups on the idempotency key and stores them.

Subrequests: an idle run makes 2 GETs (history, pulls tree). A run with new
commits adds 1-4 for the issue ledger (plus a page of history per 60 new
commits), and the folder list costs 1 GET once a day. The
first run (no cursor) backfills ``backfill_days`` with at most ``max_events``
events. Every run stops at ``max_requests`` GETs and resumes next time.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable
from urllib.parse import urlencode

from models.event import Event
from normalization.forge import (
    is_bot,
    normalize_forge_commit,
    normalize_forge_issue,
    normalize_forge_pull,
    parse_forge_time,
)


logger = logging.getLogger(__name__)

CURSOR_SOURCE = "forge"
STATE_VERSION = 1
PULL_LEDGER = "forkmesh/pulls"
BLOB_BATCH = 50
QUEUE_BATCH = 100
FOLDERS_MAX_AGE = timedelta(days=1)
_PULL_EVENT_FILE = r"^\d+-[A-Za-z0-9_-]+\.md$"

# (status, parsed JSON or None)
GetJson = Callable[[str], Awaitable[tuple[int, Any]]]


class BudgetExceeded(Exception):
    """This run has made its allowed number of forge requests."""


class ForgeError(Exception):
    """The forge answered with an error other than 404."""


@dataclass(frozen=True)
class ForgeConfig:
    url: str = "https://git.owaspblt.org"
    repo: str = "owasp-blt/BLT"
    ref: str = "main"
    bots: frozenset[str] = frozenset({"owasp-blt-actions", "forkmesh"})
    backfill_days: int = 7
    max_events: int = 300
    max_requests: int = 40
    max_history_pages: int = 5
    max_pulls_per_run: int = 10

    @property
    def web_url(self) -> str:
        return f"{self.url.rstrip('/')}/{self.repo.split('/')[-1]}"

    @classmethod
    def from_env(cls, env: Any = None) -> "ForgeConfig":
        from config import settings

        def pick(name: str, default: Any) -> Any:
            value = getattr(env, name, None) if env is not None else None
            if value is None or str(value) == "":
                return default
            return value

        def as_int(name: str, default: int) -> int:
            try:
                return int(pick(name, default))
            except (TypeError, ValueError):
                return default

        bots = str(pick("FORGE_BOT_AUTHORS", settings.forge_bot_authors))
        return cls(
            url=str(pick("FORGE_URL", settings.forge_url)),
            repo=str(pick("FORGE_REPO", settings.forge_repo)),
            ref=str(pick("FORGE_REF", settings.forge_ref)),
            bots=frozenset(b.strip().lower() for b in bots.split(",") if b.strip()),
            backfill_days=as_int("FORGE_BACKFILL_DAYS", settings.forge_backfill_days),
            max_events=as_int("FORGE_MAX_EVENTS", settings.forge_max_events),
        )


class ForgeClient:
    """Counted anonymous GETs against ``{url}/api/repo/<owner>/<repo>/``."""

    def __init__(self, get_json: GetJson, config: ForgeConfig) -> None:
        self._get_json = get_json
        self.api = f"{config.url.rstrip('/')}/api/repo/{config.repo}"
        self.max_requests = config.max_requests
        self.requests = 0

    def remaining(self) -> int:
        return self.max_requests - self.requests

    async def get(self, operation: str, params: list[tuple[str, str]] | None = None) -> Any:
        """The JSON answer, or None for 404."""
        if self.requests >= self.max_requests:
            raise BudgetExceeded()
        self.requests += 1
        query = urlencode(params or [])
        url = f"{self.api}/{operation}" + (f"?{query}" if query else "")
        status, data = await self._get_json(url)
        if status == 404:
            return None
        if status >= 400 or not isinstance(data, dict):
            raise ForgeError(f"{operation} answered {status}")
        return data


@dataclass
class PollResult:
    events: list[Event] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    requests: int = 0
    complete: bool = True
    skipped_bots: int = 0


# ---------------------------------------------------------------------------
# Poll
# ---------------------------------------------------------------------------

async def poll(
    client: ForgeClient,
    state: dict[str, Any] | None,
    config: ForgeConfig,
    now: datetime | None = None,
) -> PollResult:
    """Read what changed since ``state`` and return the new events and state.

    ``state`` is not modified; the returned state equals the input when
    nothing changed, so the caller can skip the D1 write.
    """
    now = (now or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
    old = state if isinstance(state, dict) and state.get("v") == STATE_VERSION else {}
    new = json.loads(json.dumps(old)) if old else {"v": STATE_VERSION}
    new.pop("last_error", None)
    new.pop("error_at", None)
    window_start = now - timedelta(days=config.backfill_days)
    window_ms = int(window_start.timestamp() * 1000)
    result = PollResult(state=new)
    raw: list[Event] = []

    try:
        await _refresh_folders(client, new, config, now)
        head = await _poll_commits(client, new, config, window_start, raw)
        if head:
            if new.get("issues_head") != head:
                await _poll_issues(client, new, config, head, window_ms, raw)
        await _poll_pulls(client, new, config, window_ms, raw)
    except BudgetExceeded:
        result.complete = False
        logger.warning("forge poll stopped at %d requests; the next run continues", client.requests)

    events: list[Event] = []
    for event in raw:
        if is_bot(event.actor_name, config.bots):
            result.skipped_bots += 1
            continue
        events.append(event)
    events.sort(key=lambda e: (e.timestamp, e.idempotency_key))
    if len(events) > config.max_events:
        events = events[-config.max_events:]
    result.events = events
    result.requests = client.requests
    return result


async def _poll_commits(
    client: ForgeClient,
    state: dict[str, Any],
    config: ForgeConfig,
    window_start: datetime,
    out: list[Event],
) -> str | None:
    """Collect commits newer than the cursor; returns main's head sha."""
    known = state.get("commit_sha")
    known_at = parse_forge_time(state.get("commit_at"))
    # History is not date-ordered (imported subtrees interleave), so the date
    # bound only filters; the stop is the known sha.
    floor = (known_at - timedelta(days=1)) if (known and known_at) else window_start
    folders = frozenset(state.get("folders") or []) or None
    seen: set[str] = set()
    head: str | None = None
    head_at: str | None = None
    ref = config.ref
    for _ in range(config.max_history_pages):
        data = await client.get("history", [("ref", ref)])
        commits = [c for c in (data or {}).get("commits") or [] if isinstance(c, dict)]
        if not commits:
            break
        if head is None:
            head = str(commits[0].get("hash") or "")
            head_at = str(commits[0].get("date") or "")
            if head and head == known:
                return head
        found_known = False
        all_old = True
        for commit in commits:
            sha = str(commit.get("hash") or "")
            if not sha or sha in seen:
                continue
            seen.add(sha)
            if sha == known:
                found_known = True
                break
            when = parse_forge_time(commit.get("date"))
            if when is None or when < floor:
                continue
            all_old = False
            if len(str(commit.get("parents") or "").split()) > 1:
                continue  # merge commits repeat the work they merge
            event = normalize_forge_commit(commit, web_url=config.web_url, folders=folders)
            if event is not None:
                out.append(event)
        if found_known or all_old:
            break
        parents = str(commits[-1].get("parents") or "").split()
        if not parents:
            break
        ref = parents[0]
    if head:
        state["commit_sha"] = head
        state["commit_at"] = head_at
    return head


async def _refresh_folders(
    client: ForgeClient, state: dict[str, Any], config: ForgeConfig, now: datetime,
) -> None:
    """The monorepo's top-level folders (for commit attribution), once a day."""
    checked = parse_forge_time(state.get("folders_at"))
    if state.get("folders") and checked and now - checked < FOLDERS_MAX_AGE:
        return
    data = await client.get("tree", [("path", ""), ("ref", config.ref)])
    names = sorted(
        str(e.get("name") or "").lower()
        for e in (data or {}).get("entries") or []
        if e.get("type") == "tree" and not str(e.get("name") or ".").startswith(".")
    )
    if names:
        state["folders"] = names
    state["folders_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")


def _numbered(tree: Any) -> dict[str, str]:
    found: dict[str, str] = {}
    for entry in (tree or {}).get("entries") or []:
        name = str(entry.get("name") or "")
        if entry.get("type") == "tree" and name.isdigit():
            found[name] = str(entry.get("oid") or "")
    return found


async def _poll_issues(
    client: ForgeClient,
    state: dict[str, Any],
    config: ForgeConfig,
    head: str,
    window_ms: int,
    out: list[Event],
) -> None:
    root = await client.get("tree", [("path", ".forkmesh/issues"), ("ref", head)])
    seen_dirs = state.get("issue_dirs") or {}
    dirs: dict[str, str] = {}
    listed: dict[str, tuple[str, str]] = {}
    for number, oid in _numbered(root).items():  # older layout without open/closed
        listed[number] = (oid, f".forkmesh/issues/{number}/issue-{number}.json")
    for entry in (root or {}).get("entries") or []:
        name = entry.get("name")
        if entry.get("type") != "tree" or name not in ("open", "closed"):
            continue
        dirs[name] = str(entry.get("oid") or "")
        if seen_dirs.get(name) == dirs[name]:
            continue
        sub = await client.get("tree", [("path", f".forkmesh/issues/{name}"), ("ref", head)])
        for number, oid in _numbered(sub).items():
            listed[number] = (oid, f".forkmesh/issues/{name}/{number}/issue-{number}.json")

    issues: dict[str, list] = state.setdefault("issues", {})
    folders = frozenset(state.get("folders") or []) or None
    stale = sorted(
        (n for n, (oid, _) in listed.items() if (issues.get(n) or [None])[0] != oid),
        key=int,
    )
    for start in range(0, len(stale), BLOB_BATCH):
        chunk = stale[start:start + BLOB_BATCH]
        data = await client.get("blobs", [("path", listed[n][1]) for n in chunk] + [("ref", head)])
        blobs = (data or {}).get("blobs") or {}
        for number in chunk:
            oid, path = listed[number]
            text = _blob_text(blobs.get(path))
            if text is None:
                continue  # not in this answer (truncated?): stays stale, read again later
            try:
                record = json.loads(text)
            except ValueError:
                record = None
            previous = issues.get(number)
            after = int(previous[1]) if previous else window_ms
            events, newest = normalize_forge_issue(
                record or {}, web_url=config.web_url, after_ms=after, folders=folders,
            ) if isinstance(record, dict) else ([], after)
            out.extend(events)
            issues[number] = [oid, max(newest, after)]
    state["issue_dirs"] = dirs
    state["issues_head"] = head


async def _poll_pulls(
    client: ForgeClient,
    state: dict[str, Any],
    config: ForgeConfig,
    window_ms: int,
    out: list[Event],
) -> None:
    import re

    tree = await client.get("tree", [("path", ".forkmesh/pulls"), ("ref", PULL_LEDGER)])
    if tree is None:
        return  # no ledger branch yet: no pull requests
    commit = str(tree.get("commit") or "")
    listed: dict[str, tuple[str, str]] = {n: (oid, commit) for n, oid in _numbered(tree).items()}
    for number, ref in (tree.get("pullRefs") or {}).items():
        if str(number).isdigit() and str(number) not in listed and ref:
            listed[str(number)] = (f"ref:{ref}", str(ref))
    pulls: dict[str, dict] = state.setdefault("pulls", {})
    stale = sorted(
        (n for n, (oid, _) in listed.items() if (pulls.get(n) or {}).get("oid") != oid),
        key=int,
    )
    if not stale:
        state["pulls_commit"] = commit
        return

    folders = frozenset(state.get("folders") or []) or None
    pattern = re.compile(_PULL_EVENT_FILE)
    # Each stale pull needs its file list (1 GET) and its files (shared GETs);
    # leave room for the blobs reads.
    batch = stale[: max(0, min(config.max_pulls_per_run, (client.remaining() - 2) // 2))]
    wanted: dict[str, list[str]] = {}
    for number in batch:
        oid, ref = listed[number]
        folder = f".forkmesh/pulls/{number}"
        files = await client.get("tree", [("path", folder), ("ref", ref)])
        names = [
            str(e.get("name") or "") for e in (files or {}).get("entries") or []
            if e.get("type") == "blob"
        ]
        wanted[number] = [f"{folder}/pull.md"] + [
            f"{folder}/{n}" for n in names if pattern.match(n)
        ]
    texts: dict[str, str | None] = {}
    by_ref: dict[str, list[str]] = {}
    for number, paths in wanted.items():
        by_ref.setdefault(listed[number][1], []).extend(paths)
    for ref, paths in by_ref.items():
        for start in range(0, len(paths), BLOB_BATCH):
            chunk = paths[start:start + BLOB_BATCH]
            data = await client.get("blobs", [("path", p) for p in chunk] + [("ref", ref)])
            blobs = (data or {}).get("blobs") or {}
            for path in chunk:
                texts[path] = _blob_text(blobs.get(path))
    for number, paths in wanted.items():
        previous = pulls.get(number)
        events, seen = normalize_forge_pull(
            int(number),
            texts.get(paths[0]),
            {p: texts.get(p) for p in paths[1:]},
            web_url=config.web_url,
            previous=previous,
            since_ms=window_ms,
            folders=folders,
        )
        out.extend(events)
        # An unreadable pull.md keeps what was known, so the folder is not re-read every run.
        seen = seen if seen is not None else {"ts": 0, "status": "unknown", **(previous or {})}
        pulls[number] = {**seen, "oid": listed[number][0]}
    if len(batch) == len(stale):
        state["pulls_commit"] = commit


def _blob_text(blob: Any) -> str | None:
    if blob is None:
        return None
    if isinstance(blob, str):
        return blob
    content = blob.get("content") or blob.get("text") or ""
    if blob.get("encoding") == "base64":
        import base64

        try:
            return base64.b64decode(content).decode("utf-8", "replace")
        except ValueError:
            return ""
    return content


# ---------------------------------------------------------------------------
# Worker glue
# ---------------------------------------------------------------------------

async def js_get_json(url: str) -> tuple[int, Any]:
    """GET ``url`` with the Workers ``fetch`` (one subrequest)."""
    from js import Object, fetch
    from pyodide.ffi import to_js

    options = to_js(
        {"headers": {"Accept": "application/json", "User-Agent": "BLT-Hackerhouse/1.0"}},
        dict_converter=Object.fromEntries,
    )
    response = await fetch(url, options)
    status = int(response.status)
    text = await response.text()
    if status >= 400:
        return status, None
    try:
        return status, json.loads(text)
    except ValueError:
        return 502, None


def _to_js(value: Any) -> Any:
    try:
        from js import Object
        from pyodide.ffi import to_js
    except ImportError:  # tests and local runs
        return value
    return to_js(value, dict_converter=Object.fromEntries)


async def enqueue_events(queue: Any, events: list[Event]) -> int:
    """Send events to the pipeline queue as JSON strings, 100 per ``sendBatch``."""
    bodies = [json.dumps(e.model_dump(mode="json")) for e in events]
    for start in range(0, len(bodies), QUEUE_BATCH):
        chunk = [{"body": body} for body in bodies[start:start + QUEUE_BATCH]]
        await queue.sendBatch(_to_js(chunk))
    return len(bodies)


async def run_forge_poll(
    env: Any,
    *,
    get_json: GetJson | None = None,
    now: datetime | None = None,
    config: ForgeConfig | None = None,
) -> dict[str, Any]:
    """One scheduled poll: read the cursor, poll, enqueue, save the cursor if it changed."""
    from storage import CursorQueries

    config = config or ForgeConfig.from_env(env)
    now = now or datetime.now(tz=timezone.utc)
    cursors = CursorQueries(env.HH_DB)
    stored = await cursors.get_state(CURSOR_SOURCE)
    state = stored["state"] if stored else {}
    total = stored["last_seen_id"] if stored else 0
    client = ForgeClient(get_json or js_get_json, config)
    try:
        result = await poll(client, state, config, now)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"[:300]
        logger.warning("forge poll failed: %s", error)
        if state.get("last_error") != error:
            failed = dict(state or {"v": STATE_VERSION})
            failed["last_error"] = error
            failed["error_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            await cursors.save_state(CURSOR_SOURCE, failed, total)
        return {"ok": False, "error": error, "requests": client.requests}

    sent = 0
    if result.events:
        sent = await enqueue_events(env.PIPELINE_QUEUE, result.events)
    if stored is None or result.state != state:
        await cursors.save_state(CURSOR_SOURCE, result.state, total + sent)
    summary = {
        "ok": True,
        "events": sent,
        "skipped_bots": result.skipped_bots,
        "requests": result.requests,
        "complete": result.complete,
    }
    logger.info("forge poll", extra=summary)
    return summary
