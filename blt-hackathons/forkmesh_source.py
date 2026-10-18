"""Hackathon data from a ForkMesh forge (git.owaspblt.org), one monorepo filtered by folder.

ForkMesh keeps collaboration records in git, and its public read API serves them:

- pull requests: the ``forkmesh/pulls`` ledger branch, ``.forkmesh/pulls/<n>/pull.md`` (front
  matter: title, status open/closed/merged/deleted, ts, authorName, mergedAt, derive, creation and
  merge oids), ``changes.patch`` / ``commits.mbox`` for patch-backed pulls, and one
  ``NNNN-<type>.md`` file per event (``review`` with state approved/changes_requested/commented,
  ``comment``, ``line-comment``, ...). A pull the aggregate ledger has not caught up with is listed
  under ``pullRefs`` in the tree answer and read from its own ``forkmesh/pull/<n>`` commit.
- issues: ``.forkmesh/issues/{open,closed}/<n>/issue-<n>.json`` on the default branch.

Reads used (all ``GET {url}/api/repo/<owner>/<repo>/...``, anonymous):
``tree?path=&ref=`` (listing with each entry's git oid), ``blobs?path=..&ref=`` (up to 50 files per
call) and ``compare?base=&head=`` (mbox with the diff, for branch-backed pulls).

Incremental: the cache keeps each pull and issue folder's git tree oid. A run lists the folders
(three requests) and re-reads only those whose oid changed, so a steady-state refresh is a handful
of requests. Resumable: a run that reaches its deadline keeps what it read; the next run continues
with the folders that are still stale.

Per-project attribution (the monorepo has one folder per project):
1. a pull belongs to every top-level folder its changes touch (``changes.patch``, ``commits.mbox``
   or the compare diff); ``.forkmesh/<folder>--<name>.yml`` workflows count for ``<folder>``;
2. with no readable diff, a ``<folder>:`` or ``[<folder>]`` title prefix;
3. an issue belongs to the folders named by its labels (``blt-leaf`` or ``project:blt-leaf``),
   else to its title prefix.
Items that match none of a hackathon's folders do not count for it (unless its paths are ``*``).
"""

import base64
import json
import logging
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

DEFAULT_URL = "https://git.owaspblt.org"
PULL_LEDGER = "forkmesh/pulls"
BLOB_BATCH = 50
CACHE_VERSION = 1
REVIEW_TYPES = {"review", "comment", "line-comment", "thread-comment"}
SHARED = "(shared)"


class DeadlineExceeded(Exception):
    """The run's time budget is spent; stop and keep what was read."""


class Deadline:
    """A monotonic time budget shared by every request of one run."""

    def __init__(self, seconds=None, clock=time.monotonic):
        self.clock = clock
        self.end = clock() + seconds if seconds else None

    def remaining(self):
        return float("inf") if self.end is None else self.end - self.clock()

    def expired(self):
        return self.remaining() <= 0

    def check(self):
        if self.expired():
            raise DeadlineExceeded()


def ms_to_iso(value):
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    if ms <= 0:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_front_matter(text):
    """Return (values, body) for a ``---`` front-matter document."""
    lines = (text or "").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text or ""
    values = {}
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            return values, "\n".join(lines[index + 1:])
        key, sep, value = line.partition(":")
        if sep:
            values[key.strip()] = value.strip()
    return values, ""


DIFF_PATH = re.compile(r"^diff --git a/(\S+) b/(\S+)", re.MULTILINE)


def diff_paths(text):
    paths = set()
    for old, new in DIFF_PATH.findall(text or ""):
        paths.add(old)
        paths.add(new)
    return sorted(paths)


def path_project(path):
    """The project folder a changed file belongs to, or SHARED for repository-wide files."""
    parts = path.split("/")
    if len(parts) == 1:
        return SHARED
    if parts[0] == ".forkmesh" and len(parts) == 2 and "--" in parts[1]:
        return parts[1].split("--", 1)[0].lower()
    if parts[0].startswith("."):
        return SHARED
    return parts[0].lower()


TITLE_PREFIX = re.compile(r"^\s*(?:\[([A-Za-z0-9_.-]+)\]|([A-Za-z0-9_.-]+)\s*:)")


def title_project(title):
    match = TITLE_PREFIX.match(title or "")
    return (match.group(1) or match.group(2)).lower() if match else ""


def label_projects(labels):
    found = []
    for label in labels or []:
        name = str(label.get("name") if isinstance(label, dict) else label).strip().lower()
        if name.startswith("project:"):
            name = name[len("project:"):].strip()
        if name:
            found.append(name)
    return found


class ForkMeshClient:
    """Anonymous reads from one repository's public API."""

    def __init__(self, url=DEFAULT_URL, owner="owasp-blt", repo="BLT", deadline=None,
                 opener=urlopen, sleep=time.sleep, retries=3):
        self.url = url.rstrip("/")
        self.api = f"{self.url}/api/repo/{owner}/{repo}"
        self.deadline = deadline or Deadline()
        self.opener = opener
        self.sleep = sleep
        self.retries = retries
        self.requests = 0

    def get(self, operation, params=()):
        """GET one operation; None for 404, DeadlineExceeded when the budget is spent."""
        query = urlencode(list(params))
        url = f"{self.api}/{operation}" + (f"?{query}" if query else "")
        for attempt in range(self.retries):
            self.deadline.check()
            self.requests += 1
            try:
                request = Request(url, headers={
                    "Accept": "application/json",
                    "User-Agent": "BLT-Hackathons-Stats-Fetcher/2.0",
                })
                timeout = max(1, min(30, self.deadline.remaining()))
                with self.opener(request, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if exc.code == 404:
                    return None
                if exc.code in (429, 502, 503, 504) and attempt < self.retries - 1:
                    wait = int(exc.headers.get("Retry-After", "0") or 0) if exc.headers else 0
                    wait = min(max(wait, 5 * (attempt + 1)), 120, max(self.deadline.remaining() - 1, 0))
                    logger.warning("ForkMesh %s answered %d; retrying in %ds", operation, exc.code, wait)
                    self.sleep(wait)
                    continue
                raise
            except URLError:
                if attempt < self.retries - 1:
                    self.sleep(min(5 * (attempt + 1), max(self.deadline.remaining() - 1, 0)))
                    continue
                raise
        return None

    def tree(self, path, ref=""):
        params = [("path", path)]
        if ref:
            params.append(("ref", ref))
        return self.get("tree", params)

    def blobs(self, paths, ref=""):
        """Map path -> text (None when missing), reading BLOB_BATCH paths per request."""
        found = {}
        paths = list(paths)
        for start in range(0, len(paths), BLOB_BATCH):
            chunk = paths[start:start + BLOB_BATCH]
            params = [("path", p) for p in chunk] + ([("ref", ref)] if ref else [])
            data = self.get("blobs", params) or {}
            for path in chunk:
                found[path] = blob_text((data.get("blobs") or {}).get(path))
        return found

    def compare(self, base, head):
        return self.get("compare", [("base", base), ("head", head)])


def blob_text(blob):
    if blob is None:
        return None
    if isinstance(blob, str):
        return blob
    content = blob.get("content") or blob.get("text") or ""
    if blob.get("encoding") == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", "replace")
        except ValueError:
            return ""
    return content


def numbered_dirs(tree):
    """{number: oid} for the numeric sub-folders of a tree answer."""
    found = {}
    for entry in (tree or {}).get("entries") or []:
        name = str(entry.get("name") or "")
        if entry.get("type") == "tree" and name.isdigit():
            found[name] = str(entry.get("oid") or "")
    return found


def new_cache():
    return {"version": CACHE_VERSION, "pulls": {}, "issues": {}, "about": {}, "complete": False}


def user_entry(base_url, name, key=""):
    login = name or (key[:12] if key else "unknown")
    return {"login": login, "avatar_url": "", "html_url": f"{base_url}/@{login}"}


def read_pull(client, web, number, ref):
    """Read one pull folder at an immutable ledger commit and normalize it."""
    folder = f".forkmesh/pulls/{number}"
    tree = client.tree(folder, ref)
    names = [str(e.get("name") or "") for e in (tree or {}).get("entries") or [] if e.get("type") == "blob"]
    wanted = ["pull.md"] + [n for n in names if re.match(r"^\d+-[A-Za-z0-9_-]+\.md$", n)]
    for extra in ("changes.patch", "commits.mbox"):
        if extra in names:
            wanted.append(extra)
    files = client.blobs([f"{folder}/{n}" for n in wanted], ref)
    meta, _ = parse_front_matter(files.get(f"{folder}/pull.md") or "")
    if not meta:
        return None
    status = meta.get("status", "open").lower()
    if status == "deleted":
        return {"deleted": True}
    paths = diff_paths((files.get(f"{folder}/changes.patch") or "") + (files.get(f"{folder}/commits.mbox") or ""))
    if not paths and meta.get("derive") == "branch":
        base = meta.get("mergeBase") or meta.get("creationBaseOid")
        head = meta.get("mergeHead") or meta.get("creationHeadOid")
        if base and head:
            compared = client.compare(base, head) or {}
            paths = diff_paths(compared.get("commits") or compared.get("patch") or "")
    url = f"{web}/pulls/{number}"
    author = user_entry(client.url, meta.get("authorName"), meta.get("author", ""))
    reviews = []
    updated = int(meta.get("mergedAt") or 0) or int(meta.get("ts") or 0)
    for name in sorted(wanted):
        if name == "pull.md" or not name.endswith(".md"):
            continue
        event, _ = parse_front_matter(files.get(f"{folder}/{name}") or "")
        kind = event.get("type", "")
        try:
            updated = max(updated, int(event.get("ts") or 0))
        except ValueError:
            pass
        if kind not in REVIEW_TYPES:
            continue
        state = event.get("state", "").lower() if kind == "review" else ""
        reviews.append({
            "id": f"{number}:{event.get('id') or name}",
            "state": {"approved": "APPROVED", "changes_requested": "CHANGES_REQUESTED"}.get(state, "COMMENTED"),
            "submitted_at": ms_to_iso(event.get("ts")),
            "html_url": url,
            "user": user_entry(client.url, event.get("authorName"), event.get("author", "")),
        })
    merged = status in ("merged", "closed-merged")
    return {
        "number": int(number),
        "title": meta.get("title", ""),
        "state": "open" if status == "open" else "closed",
        "created_at": ms_to_iso(meta.get("ts")),
        "merged_at": (ms_to_iso(meta.get("mergedAt")) or ms_to_iso(updated)) if merged else None,
        "updated_at": ms_to_iso(updated),
        "html_url": url,
        "user": author,
        "pathProjects": sorted({path_project(p) for p in paths}),
        "titleProject": title_project(meta.get("title")),
        "reviews": reviews,
    }


def normalize_issue(raw, web, base_url):
    if not isinstance(raw, dict) or not raw.get("number"):
        return None
    status = str(raw.get("status") or "open").lower()
    closed_at = None
    if status != "open":
        closes = [e.get("ts") for e in raw.get("events") or []
                  if e.get("type") in ("close", "closed") or (e.get("type") == "status" and e.get("state") == "closed")]
        closed_at = ms_to_iso(max(closes)) if closes else ms_to_iso(raw.get("updatedAt"))
    return {
        "number": int(raw["number"]),
        "title": raw.get("title", ""),
        "state": "open" if status == "open" else "closed",
        "created_at": ms_to_iso(raw.get("createdAt")),
        "closed_at": closed_at,
        "html_url": f"{web}/issues/{raw['number']}",
        "user": user_entry(base_url, raw.get("authorName"), raw.get("author", "")),
        "labelProjects": label_projects(raw.get("labels")),
        "titleProject": title_project(raw.get("title")),
    }


def sync_pulls(client, cache, web):
    tree = client.tree(".forkmesh/pulls", PULL_LEDGER)
    listed = {}
    if tree:
        commit = str(tree.get("commit") or "")
        for number, oid in numbered_dirs(tree).items():
            listed[number] = (oid, commit)
        for number, ref in (tree.get("pullRefs") or {}).items():
            if str(number).isdigit() and str(number) not in listed and ref:
                listed[str(number)] = (f"ref:{ref}", str(ref))
    pulls = cache.setdefault("pulls", {})
    for number in list(pulls):
        if number not in listed:
            del pulls[number]
    stale = [n for n, (oid, _) in listed.items() if (pulls.get(n) or {}).get("oid") != oid]
    for number in sorted(stale, key=int, reverse=True):
        oid, ref = listed[number]
        record = read_pull(client, web, number, ref)
        if record is not None:
            pulls[number] = {"oid": oid, "record": record}
    return len(stale)


def sync_issues(client, cache, web):
    root = client.tree(".forkmesh/issues")
    listed = {}
    if root:
        commit = str(root.get("commit") or "")
        for number, oid in numbered_dirs(root).items():  # older layout without open/closed
            listed[number] = (oid, f".forkmesh/issues/{number}/issue-{number}.json", commit)
        for entry in root.get("entries") or []:
            if entry.get("type") == "tree" and entry.get("name") in ("open", "closed"):
                sub = client.tree(f".forkmesh/issues/{entry['name']}", commit) or {}
                for number, oid in numbered_dirs(sub).items():
                    listed[number] = (oid, f".forkmesh/issues/{entry['name']}/{number}/issue-{number}.json", commit)
    issues = cache.setdefault("issues", {})
    for number in list(issues):
        if number not in listed:
            del issues[number]
    stale = [n for n, (oid, _, _) in listed.items() if (issues.get(n) or {}).get("oid") != oid]
    for start in range(0, len(stale), BLOB_BATCH):
        chunk = stale[start:start + BLOB_BATCH]
        texts = client.blobs([listed[n][1] for n in chunk], listed[chunk[0]][2])
        for number in chunk:
            oid, path, _ = listed[number]
            try:
                record = normalize_issue(json.loads(texts.get(path) or "null"), web, client.url)
            except ValueError:
                record = None
            issues[number] = {"oid": oid, "record": record}
    return len(stale)


def sync_about(client, cache, folders, max_age_seconds=86400, now=None):
    """Folder descriptions from ``<folder>/.forkmesh/info.json`` (folder About boxes), daily."""
    now = now or time.time()
    about = cache.setdefault("about", {})
    if not folders:
        return
    if now - about.get("_checked", 0) < max_age_seconds and all(f in about for f in folders):
        return
    texts = client.blobs([f"{f}/.forkmesh/info.json" for f in folders], "")
    for folder in folders:
        try:
            info = json.loads(texts.get(f"{folder}/.forkmesh/info.json") or "{}")
        except ValueError:
            info = {}
        about[folder] = {"description": (info.get("about") or info.get("description")) if isinstance(info, dict) else None}
    about["_checked"] = now


def sync_repository(client, cache, web, folders=()):
    """Bring the cache up to date as far as the deadline allows. Returns (cache, complete)."""
    if not isinstance(cache, dict) or cache.get("version") != CACHE_VERSION:
        cache = new_cache()
    complete = False
    try:
        changed_pulls = sync_pulls(client, cache, web)
        changed_issues = sync_issues(client, cache, web)
        logger.info("ForkMesh sync: %d pull(s) and %d issue(s) re-read, %d request(s)",
                    changed_pulls, changed_issues, client.requests)
        complete = True
        sync_about(client, cache, [f for f in folders if f != "*"])
    except DeadlineExceeded:
        logger.warning("ForkMesh sync stopped at the time budget after %d request(s); the next run continues",
                       client.requests)
    cache["complete"] = complete
    cache["syncedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return cache, complete


def in_window(start_dt, end_dt, *stamps):
    for stamp in stamps:
        if stamp:
            value = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if start_dt <= value <= end_dt:
                return True
    return False


def attributed(projects_from_paths, title_prefix, folders):
    """Folders an item counts for in a hackathon whose eligible folders are ``folders``."""
    everything = "*" in folders
    if projects_from_paths:
        chosen = sorted(set(projects_from_paths)) if everything else sorted(set(projects_from_paths) & folders)
        if chosen or not everything:
            return chosen
    if title_prefix and (everything or title_prefix in folders):
        return [title_prefix]
    return [SHARED] if everything else []


def hackathon_inputs(cache, folders, start_dt, end_dt, web):
    """(prs, reviews, issues, repositories, repo_data) for process_hackathon_stats."""
    folders = {f.lower() for f in folders}
    prs, reviews, issues = [], [], []
    for entry in (cache.get("pulls") or {}).values():
        record = entry.get("record") or {}
        if record.get("deleted") or not record.get("created_at"):
            continue
        projects = attributed(record.get("pathProjects"), record.get("titleProject"), folders)
        if not projects or not in_window(start_dt, end_dt, record["created_at"], record.get("merged_at")):
            continue
        pr = {k: v for k, v in record.items() if k not in ("reviews", "pathProjects", "titleProject")}
        pr.update({"repository": projects[0], "repositories": projects})
        prs.append(pr)
        for review in record.get("reviews") or []:
            reviews.append({**review, "repository": projects[0], "pull_request_url": record["html_url"],
                            "pull_request_title": record.get("title", ""),
                            "pull_request_author": record["user"]["login"]})
    for entry in (cache.get("issues") or {}).values():
        record = entry.get("record")
        if not record or not record.get("created_at"):
            continue
        labelled = [p for p in record.get("labelProjects") or [] if "*" in folders or p in folders]
        projects = labelled or attributed([], record.get("titleProject"), folders)
        if not projects or not in_window(start_dt, end_dt, record["created_at"], record.get("closed_at")):
            continue
        issues.append({**record, "repository": projects[0], "repositories": projects})
    if "*" in folders:
        repositories = sorted({p for item in prs + issues for p in item["repositories"]})
    else:
        repositories = sorted(folders)
    about = cache.get("about") or {}
    repo_data = [{
        "full_name": folder,
        "description": (about.get(folder) or {}).get("description"),
        "html_url": f"{web}/tree/main/{folder}" if folder != SHARED else web,
        "pulls_url": f"{web}/pulls",
        "issues_url": f"{web}/issues",
    } for folder in repositories]
    return prs, reviews, issues, repositories, repo_data
