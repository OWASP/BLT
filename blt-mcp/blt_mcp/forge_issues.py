"""Read BLT issues from the git.owaspblt.org issue ledger (anonymous, async).

A small, self-contained copy of the reader in ``scripts/forkmesh/ledger.py`` (that module lives
outside this package, so an installed blt-mcp cannot import it). Issues are stored on ``main`` as
``.forkmesh/issues/{open,closed}/<n>/issue-<n>.json``; the forge's ``/issues`` API answers 401 to
anonymous callers, so the ledger is read through ``tree`` and ``blobs`` instead.
"""

import base64
import json
import os
import re
import time

import httpx

DEFAULT_URL = "https://git.owaspblt.org"
OWNER, REPO = "owasp-blt", "BLT"
BLOB_BATCH = 50
CACHE_SECONDS = 300
EXTRA_FOLDERS = ("my-gsoc-tool", "coderabbit")
TITLE_PREFIX = re.compile(r"^\s*(?:\[([A-Za-z0-9_.-]+)\]|([A-Za-z0-9_.-]+)\s*:)")

_cache: dict = {}


def base_url() -> str:
    return (os.getenv("FORKMESH_URL") or DEFAULT_URL).rstrip("/")


def web_url() -> str:
    return f"{base_url()}/BLT"


def issue_url(number) -> str:
    return f"{web_url()}/issues/{number}"


async def _get(client: httpx.AsyncClient, operation: str, params) -> dict | None:
    resp = await client.get(
        f"{base_url()}/api/repo/{OWNER}/{REPO}/{operation}",
        params=list(params),
        headers={"Accept": "application/json", "User-Agent": "BLT-MCP"},
        timeout=30.0,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _numbered_dirs(tree) -> dict:
    found = {}
    for entry in (tree or {}).get("entries") or []:
        name = str(entry.get("name") or "")
        if entry.get("type") == "tree" and name.isdigit():
            found[name] = str(entry.get("oid") or "")
    return found


def _blob_text(blob):
    if blob is None or isinstance(blob, str):
        return blob
    content = blob.get("content") or blob.get("text") or ""
    if blob.get("encoding") == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", "replace")
        except ValueError:
            return ""
    return content


async def issues(client: httpx.AsyncClient, statuses=("open", "closed")) -> list[dict]:
    """Issue records (raw ledger JSON) in the given status folders, newest number first."""
    root = await _get(client, "tree", [("path", ".forkmesh/issues")])
    if not root:
        return []
    commit = str(root.get("commit") or "")
    paths = {n: f".forkmesh/issues/{n}/issue-{n}.json" for n in _numbered_dirs(root)}
    for entry in root.get("entries") or []:
        name = entry.get("name")
        if entry.get("type") == "tree" and name in statuses:
            sub = await _get(client, "tree", [("path", f".forkmesh/issues/{name}"), ("ref", commit)])
            for n in _numbered_dirs(sub):
                paths[n] = f".forkmesh/issues/{name}/{n}/issue-{n}.json"
    numbers = sorted(paths, key=int, reverse=True)
    found = []
    for start in range(0, len(numbers), BLOB_BATCH):
        chunk = numbers[start:start + BLOB_BATCH]
        params = [("path", paths[n]) for n in chunk] + ([("ref", commit)] if commit else [])
        blobs = ((await _get(client, "blobs", params)) or {}).get("blobs") or {}
        for n in chunk:
            try:
                record = json.loads(_blob_text(blobs.get(paths[n])) or "null")
            except ValueError:
                record = None
            if isinstance(record, dict):
                found.append(record)
    return found


async def cached_issues(client: httpx.AsyncClient, statuses=("open",), now=time.monotonic) -> list[dict]:
    """``issues()`` with a short in-process cache (CACHE_SECONDS)."""
    key = tuple(statuses)
    hit = _cache.get(key)
    if hit and now() - hit[0] < CACHE_SECONDS:
        return hit[1]
    found = await issues(client, statuses)
    _cache[key] = (now(), found)
    return found


def labels(issue: dict) -> list[str]:
    names = []
    for label in issue.get("labels") or []:
        name = label.get("name") if isinstance(label, dict) else label
        if name:
            names.append(str(name).strip().lower())
    return names


def is_open(issue: dict) -> bool:
    return str(issue.get("status") or "open").lower() == "open"


def issue_projects(issue: dict) -> list[str]:
    """Folders an issue belongs to: labels ``blt-x`` / ``project:blt-x``, else its title prefix."""
    found = []
    for name in labels(issue):
        if name.startswith("project:"):
            name = name[len("project:"):].strip()
        if name and (name.startswith("blt-") or name in EXTRA_FOLDERS):
            found.append(name)
    if found:
        return found
    match = TITLE_PREFIX.match(issue.get("title") or "")
    return [(match.group(1) or match.group(2)).lower()] if match else []


def body(issue: dict) -> str:
    """The description: the ``open`` event's body, updated by later ``edit`` events of it."""
    text, open_id = "", None
    events = [e for e in issue.get("events") or [] if isinstance(e, dict)]
    for event in sorted(events, key=lambda e: int(e.get("ts") or 0)):
        if event.get("type") == "open":
            text, open_id = event.get("body") or "", event.get("id")
        elif event.get("type") == "edit" and open_id and event.get("target") == open_id:
            text = event.get("body") or ""
    return text or issue.get("body") or ""
