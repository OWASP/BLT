"""Forge (git.owaspblt.org) normalizer.

Turns the BLT monorepo's commits, issue records and pull ledger files into
``Event`` objects with ``source = "forge"``. Every event carries a stable
``metadata["dedup_key"]`` (commit sha, issue event id, pull file), so the
idempotency key does not depend on the actor or the second it happened in.

Formats (read anonymously, see ``blt-hackathons/forkmesh_source.py``):

- ``history?ref=main``: ``{"commits": [{"hash", "author", "date", "subject", "parents"}]}``;
- issues: ``.forkmesh/issues/{open,closed}/<n>/issue-<n>.json`` with ``events``
  (``open``, ``comment``, ``close``, ``status``, ``vote``...), times in ms;
- pulls: ``.forkmesh/pulls/<n>/pull.md`` front matter (title, status, ts,
  authorName, mergedAt) and one ``NNNN-<type>.md`` file per pull event.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from models.event import Event


MONOREPO = "BLT"
BODY_LIMIT = 280
PULL_NOTE_TYPES = {"comment", "review", "line-comment", "thread-comment"}
_PREFIX = re.compile(r"^\s*(?:\[([A-Za-z0-9_.-]+)\]|([A-Za-z0-9_.\-, ]+?)\s*:)")
_BOT_SUFFIXES = ("[bot]", "-bot", "_bot")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_forge_time(value: Any) -> datetime | None:
    """An aware UTC datetime from an ISO string (any offset) or epoch milliseconds."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        try:
            ms = int(value)
        except (TypeError, ValueError):
            return None
        if ms <= 0:
            return None
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(microsecond=0)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def to_ms(value: Any) -> int:
    when = parse_forge_time(value)
    return int(when.timestamp() * 1000) if when else 0


def is_bot(name: str | None, bots: set[str] | frozenset[str]) -> bool:
    """True for automation authors (``owasp-blt-actions``, ``forkmesh``, ``*[bot]``)."""
    lowered = (name or "").strip().lower()
    if not lowered:
        return True
    return lowered in bots or lowered.endswith(_BOT_SUFFIXES)


def subject_folders(subject: str | None, folders: set[str] | frozenset[str] | None = None) -> list[str]:
    """Project folders named by a ``<folder>:``, ``a, b:`` or ``[folder]`` subject prefix.

    With ``folders`` (the monorepo's top-level folders), names that are not
    folders are dropped, so "CI: ..." or "Eight projects: ..." stay unattributed.
    """
    match = _PREFIX.match(subject or "")
    if not match:
        return []
    raw = match.group(1) or match.group(2) or ""
    found: list[str] = []
    for part in raw.split(","):
        name = part.strip().lower()
        if not name or " " in name:
            continue
        if folders is not None and name not in folders:
            continue
        if name not in found:
            found.append(name)
    return found


def label_folders(labels: Any) -> list[str]:
    found: list[str] = []
    for label in labels or []:
        name = str(label.get("name") if isinstance(label, dict) else label).strip().lower()
        if name.startswith("project:"):
            name = name[len("project:"):].strip()
        if name and name not in found:
            found.append(name)
    return found


def _excerpt(text: Any) -> str | None:
    text = str(text or "").strip()
    if not text:
        return None
    return text if len(text) <= BODY_LIMIT else text[: BODY_LIMIT - 1].rstrip() + "…"


def parse_front_matter(text: str | None) -> tuple[dict[str, str], str]:
    """Return (values, body) for a ``---`` front-matter document."""
    lines = (text or "").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text or ""
    values: dict[str, str] = {}
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            return values, "\n".join(lines[index + 1:])
        key, sep, value = line.partition(":")
        if sep:
            values[key.strip()] = value.strip()
    return values, ""


# ---------------------------------------------------------------------------
# Commits
# ---------------------------------------------------------------------------

def normalize_forge_commit(
    commit: dict[str, Any],
    *,
    web_url: str,
    folders: set[str] | frozenset[str] | None = None,
) -> Event | None:
    """One ``commit_pushed`` event for a commit on main, or None when unusable."""
    sha = str(commit.get("hash") or "")
    author = str(commit.get("author") or "").strip()
    when = parse_forge_time(commit.get("date"))
    if not sha or not author or when is None:
        return None
    subject = str(commit.get("subject") or "").strip()
    projects = subject_folders(subject, folders)
    return Event(
        source="forge",
        event_type="commit_pushed",
        actor_id=author,
        actor_name=author,
        repository=projects[0] if projects else MONOREPO,
        timestamp=when,
        metadata={
            "dedup_key": sha,
            "title": subject or sha[:7],
            "commit_sha": sha,
            "commit_title": subject,
            "url": f"{web_url}/commit/{sha}",
            "folders": projects,
        },
    )


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

def _issue_event_type(event: dict[str, Any]) -> str | None:
    kind = str(event.get("type") or "").lower()
    if kind == "open":
        return "issue_opened"
    if kind == "comment":
        return "note_added"
    if kind in ("close", "closed"):
        return "issue_closed"
    if kind == "status" and str(event.get("state") or event.get("status") or "").lower() == "closed":
        return "issue_closed"
    return None


def normalize_forge_issue(
    raw: dict[str, Any],
    *,
    web_url: str,
    after_ms: int = 0,
    folders: set[str] | frozenset[str] | None = None,
) -> tuple[list[Event], int]:
    """Events for one issue record that happened after ``after_ms``.

    Returns ``(events, newest_ms)``; ``newest_ms`` is the latest event time in
    the record (the caller keeps it as the issue's cursor).
    """
    if not isinstance(raw, dict) or not raw.get("number"):
        return [], after_ms
    number = int(raw["number"])
    title = str(raw.get("title") or f"Issue #{number}")
    labelled = [f for f in label_folders(raw.get("labels")) if folders is None or f in folders]
    projects = labelled or subject_folders(title, folders)
    repository = projects[0] if projects else MONOREPO
    url = f"{web_url}/issues/{number}"

    items = [e for e in raw.get("events") or [] if isinstance(e, dict)]
    if not any(str(e.get("type") or "").lower() == "open" for e in items) and raw.get("createdAt"):
        items.insert(0, {
            "type": "open", "id": f"open-{number}", "ts": raw.get("createdAt"),
            "authorName": raw.get("authorName"),
        })

    newest = after_ms
    events: list[Event] = []
    for item in items:
        ts = to_ms(item.get("ts"))
        newest = max(newest, ts)
        event_type = _issue_event_type(item)
        if event_type is None or ts <= after_ms:
            continue
        actor = str(item.get("authorName") or raw.get("authorName") or "").strip()
        if not actor:
            continue
        event_id = str(item.get("id") or f"{item.get('type')}-{ts}")
        metadata: dict[str, Any] = {
            "dedup_key": f"issue:{number}:{event_id}",
            "title": title if event_type != "note_added" else f"Comment on #{number}: {title}",
            "issue_number": number,
            "url": url,
            "folders": projects,
        }
        if event_type == "note_added":
            metadata["body"] = _excerpt(item.get("body"))
        events.append(Event(
            source="forge",
            event_type=event_type,
            actor_id=actor,
            actor_name=actor,
            repository=repository,
            timestamp=parse_forge_time(ts),
            metadata=metadata,
        ))
    return events, newest


# ---------------------------------------------------------------------------
# Pull requests
# ---------------------------------------------------------------------------

def normalize_forge_pull(
    number: int,
    pull_md: str | None,
    event_files: dict[str, str | None],
    *,
    web_url: str,
    previous: dict[str, Any] | None,
    since_ms: int = 0,
    folders: set[str] | frozenset[str] | None = None,
) -> tuple[list[Event], dict[str, Any] | None]:
    """Events for one pull folder, given what the last run saw of it.

    ``previous`` is ``{"ts": newest event ms, "status": status}`` or None for a
    pull this poller has not seen; ``since_ms`` bounds a first sighting (the
    backfill window). Returns ``(events, {"ts", "status"})`` or ``([], None)``
    when ``pull.md`` is unreadable.
    """
    meta, _ = parse_front_matter(pull_md)
    if not meta:
        return [], None
    status = meta.get("status", "open").lower()
    seen_ts = int((previous or {}).get("ts") or 0)
    floor_ms = max(seen_ts, since_ms)
    title = meta.get("title") or f"Pull #{number}"
    projects = subject_folders(title, folders)
    repository = projects[0] if projects else MONOREPO
    url = f"{web_url}/pulls/{number}"
    author = (meta.get("authorName") or "").strip()
    newest = seen_ts
    events: list[Event] = []

    def add(event_type: str, actor: str, ts: int, key: str, extra: dict[str, Any] | None = None) -> None:
        if not actor or ts <= 0:
            return
        events.append(Event(
            source="forge",
            event_type=event_type,
            actor_id=actor,
            actor_name=actor,
            repository=repository,
            timestamp=parse_forge_time(ts),
            metadata={
                "dedup_key": f"pull:{number}:{key}",
                "title": title,
                "pull_number": number,
                "url": url,
                "folders": projects,
                **(extra or {}),
            },
        ))

    if status == "deleted":
        return [], {"ts": seen_ts, "status": status}

    opened = to_ms(meta.get("ts"))
    newest = max(newest, opened)
    if previous is None and opened > since_ms:
        add("mr_opened", author, opened, "open")

    merged_ms = to_ms(meta.get("mergedAt"))
    newest = max(newest, merged_ms)
    was_merged = (previous or {}).get("status") in ("merged", "closed-merged")
    if status in ("merged", "closed-merged") and not was_merged and merged_ms > since_ms:
        merger = (meta.get("mergedByName") or meta.get("mergerName") or author).strip()
        add("mr_merged", merger, merged_ms, "merged")

    for name in sorted(event_files):
        values, body = parse_front_matter(event_files[name])
        ts = to_ms(values.get("ts"))
        newest = max(newest, ts)
        kind = values.get("type", "").lower()
        if kind not in PULL_NOTE_TYPES or ts <= floor_ms:
            continue
        key = values.get("id") or name.rsplit("/", 1)[-1]
        extra = {"note_kind": kind, "body": _excerpt(body)}
        if kind == "review":
            extra["review_state"] = values.get("state", "").lower() or None
        add("note_added", (values.get("authorName") or "").strip(), ts, key, extra)

    return events, {"ts": newest, "status": status}
