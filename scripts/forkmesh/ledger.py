"""Read BLT's issues, pull requests and folder history from git.owaspblt.org (anonymous).

Shared by the data generators that used to read gitlab.com/owasp-blt (README contributors,
blt-pages leaderboard, blt-design-contest showcase, blt-waypoint). It reuses the client and the
attribution rules of ``blt-hackathons/forkmesh_source.py``:

- issues: ``.forkmesh/issues/{open,closed}/<n>/issue-<n>.json`` on ``main`` (full records here:
  labels, status, events with comments and votes, authorName, timestamps in ms);
- pull requests: ``.forkmesh/pulls/<n>/pull.md`` front matter on the ``forkmesh/pulls`` ledger
  branch (no ledger yet means no pull requests);
- folder history: ``history?path=<folder>`` (60 commits per call; older pages by ``ref``).

``/issues`` and ``/pulls`` answer 401 to anonymous callers, which is why the ledgers are read.

Usage::

    import sys; sys.path.insert(0, "<repo>/scripts/forkmesh")
    import ledger
    client = ledger.client()
    for issue in ledger.issues(client):
        if "bug" in ledger.labels(issue) and "blt-pages" in ledger.issue_projects(issue): ...
"""

import json
import os
import sys
from datetime import datetime, timezone

_HACKATHONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "blt-hackathons")
if _HACKATHONS not in sys.path:
    sys.path.insert(0, _HACKATHONS)

import forkmesh_source as fs  # noqa: E402  (blt-hackathons/forkmesh_source.py)

DEFAULT_URL = fs.DEFAULT_URL
WEB_URL = f"{DEFAULT_URL}/BLT"
HISTORY_PAGE = 60

Deadline = fs.Deadline
DeadlineExceeded = fs.DeadlineExceeded
ForkMeshClient = fs.ForkMeshClient
parse_front_matter = fs.parse_front_matter
title_project = fs.title_project
path_project = fs.path_project


def client(url=None, seconds=None, **kwargs):
    """A ForkMeshClient for owasp-blt/BLT (``FORKMESH_URL`` overrides the instance)."""
    return fs.ForkMeshClient(url or os.environ.get("FORKMESH_URL") or DEFAULT_URL,
                             deadline=fs.Deadline(seconds), **kwargs)


def ms_to_iso(value):
    return fs.ms_to_iso(value)


def iso_to_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def _issue_paths(cl):
    """{number: (oid, path, commit)} for every issue folder on main."""
    root = cl.tree(".forkmesh/issues")
    listed = {}
    if not root:
        return listed
    commit = str(root.get("commit") or "")
    for number, oid in fs.numbered_dirs(root).items():  # older layout without open/closed
        listed[number] = (oid, f".forkmesh/issues/{number}/issue-{number}.json", commit)
    for entry in root.get("entries") or []:
        if entry.get("type") == "tree" and entry.get("name") in ("open", "closed"):
            sub = cl.tree(f".forkmesh/issues/{entry['name']}", commit) or {}
            for number, oid in fs.numbered_dirs(sub).items():
                listed[number] = (oid, f".forkmesh/issues/{entry['name']}/{number}/issue-{number}.json", commit)
    return listed


def issues(cl, cache=None):
    """Every issue record (the raw JSON), newest number first.

    ``cache`` (a dict, optional) keeps ``{number: {"oid", "record"}}`` between runs, so only issue
    folders whose git oid changed are read again; pass the same dict back next time.
    """
    listed = _issue_paths(cl)
    cache = cache if cache is not None else {}
    for number in list(cache):
        if number not in listed:
            del cache[number]
    stale = [n for n, (oid, _, _) in listed.items() if (cache.get(n) or {}).get("oid") != oid]
    for start in range(0, len(stale), fs.BLOB_BATCH):
        chunk = stale[start:start + fs.BLOB_BATCH]
        texts = cl.blobs([listed[n][1] for n in chunk], listed[chunk[0]][2])
        for number in chunk:
            try:
                record = json.loads(texts.get(listed[number][1]) or "null")
            except ValueError:
                record = None
            cache[number] = {"oid": listed[number][0], "record": record}
    found = [entry["record"] for entry in cache.values() if isinstance(entry.get("record"), dict)]
    return sorted(found, key=lambda r: int(r.get("number") or 0), reverse=True)


def pulls(cl):
    """Pull request front matter (title, status, ts, authorName, mergedAt, ...) with ``number``."""
    tree = cl.tree(".forkmesh/pulls", fs.PULL_LEDGER)
    if not tree:
        return []
    commit = str(tree.get("commit") or "")
    numbers = sorted(fs.numbered_dirs(tree), key=int, reverse=True)
    texts = cl.blobs([f".forkmesh/pulls/{n}/pull.md" for n in numbers], commit)
    found = []
    for number in numbers:
        meta, _ = fs.parse_front_matter(texts.get(f".forkmesh/pulls/{number}/pull.md") or "")
        if meta and meta.get("status", "").lower() != "deleted":
            found.append({**meta, "number": int(number)})
    return found


def labels(issue):
    """Lower-cased label names of an issue record."""
    names = []
    for label in issue.get("labels") or []:
        name = label.get("name") if isinstance(label, dict) else label
        if name:
            names.append(str(name).strip().lower())
    return names


def issue_projects(issue):
    """Folders an issue belongs to: labels ``blt-x`` / ``project:blt-x``, else its title prefix."""
    found = [name for name in fs.label_projects(issue.get("labels")) if name.startswith("blt-") or name in
             ("my-gsoc-tool", "coderabbit", "dot_github")]
    if found:
        return found
    prefix = fs.title_project(issue.get("title"))
    return [prefix] if prefix else []


def is_open(issue):
    return str(issue.get("status") or "open").lower() == "open"


def events(issue, kind=None):
    found = [e for e in issue.get("events") or [] if isinstance(e, dict)]
    return [e for e in found if e.get("type") == kind] if kind else found


def body(issue):
    """The issue description: the ``open`` event's body, updated by later ``edit`` events of it."""
    text, open_id = "", None
    for event in sorted(events(issue), key=lambda e: int(e.get("ts") or 0)):
        if event.get("type") == "open":
            text, open_id = event.get("body") or "", event.get("id")
        elif event.get("type") == "edit" and open_id and event.get("target") == open_id:
            text = event.get("body") or ""
    return text or issue.get("body") or ""


def comments(issue):
    """Comment events (author, authorName, body, ts), oldest first, without deleted ones."""
    deleted = {e.get("target") for e in events(issue, "delete")}
    return sorted((e for e in events(issue, "comment") if e.get("id") not in deleted),
                  key=lambda e: int(e.get("ts") or 0))


def voters(issue):
    """Distinct account names (authorName, else key) that voted for the issue on the forge."""
    names = []
    for event in events(issue, "vote"):
        name = event.get("authorName") or event.get("author")
        if name and name not in names:
            names.append(name)
    return names


def vote_count(issue):
    return max(len(voters(issue)), int(issue.get("votes") or 0))


def closed_at(issue):
    if is_open(issue):
        return None
    stamps = [e.get("ts") for e in events(issue)
              if e.get("type") in ("close", "closed") or (e.get("type") == "status" and e.get("status") == "closed")]
    return ms_to_iso(max(stamps)) if stamps else ms_to_iso(issue.get("updatedAt"))


def issue_url(number):
    return f"{WEB_URL}/issues/{number}"


def profile_url(name):
    return f"{DEFAULT_URL}/@{name}" if name else ""


def history(cl, path, since=None, max_pages=20):
    """Commits touching ``path`` (newest first), down to ``since`` (an aware datetime) if given.

    The live API returns 60 commits per call and ignores ``since``/``until`` with a path, so older
    pages are read with ``ref=<oldest commit's first parent>``.
    """
    found, seen, ref = [], set(), ""
    for _ in range(max_pages):
        params = [("path", path), ("limit", str(HISTORY_PAGE))] + ([("ref", ref)] if ref else [])
        page = (cl.get("history", params) or {}).get("commits") or []
        fresh = [c for c in page if c.get("hash") not in seen]
        if not fresh:
            break
        for commit in fresh:
            seen.add(commit.get("hash"))
            when = iso_to_dt(commit.get("date"))
            if since and when and when < since:
                return found
            found.append(commit)
        parents = str(fresh[-1].get("parents") or "").split()
        if len(page) < HISTORY_PAGE or not parents:
            break
        ref = parents[0]
    return found


def folders(root):
    """Project folders from scripts/routing/projects.tsv: [(folder, display name)]."""
    rows = []
    with open(os.path.join(root, "scripts", "routing", "projects.tsv"), encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if parts[0] and parts[0] != "-":
                rows.append((parts[0], parts[1] if len(parts) > 1 else parts[0]))
    return rows
