"""Forge source for the PR leaderboard: BLT pull requests on git.owaspblt.org.

Since the move from GitHub, pull requests live on the ForkMesh forge. Its public read API serves the
``forkmesh/pulls`` ledger branch anonymously:

- ``.forkmesh/pulls/<n>/pull.md``: front matter ``title``, ``status`` (open, closed, merged,
  closed-merged, deleted), ``ts`` (opened, ms), ``authorName``, ``mergedAt`` (ms), ``derive``,
  merge/creation oids;
- ``.forkmesh/pulls/<n>/NNNN-<type>.md``: one file per event (``review`` with ``state``,
  ``comment``, ``line-comment``, ``thread-comment``, ...), each with ``authorName`` and ``ts``;
- ``changes.patch`` / ``commits.mbox`` for patch-backed pulls (the touched folders).

The README roster ``.forkmesh/contributors/contributors.json`` (on ``main``) maps forge and GitHub
logins to display names and avatars.

Incremental sync (``sync``), run from blt-cron every 20 minutes:

1. read the cursor row (``leaderboard_forge_cursor``: ledger commit, roster, forge logins seen);
2. once a day, the roster (1 GET of the raw JSON; written back only when it changed);
3. the ledger tree (1 GET). 404 means no ledger yet: nothing to do. Same commit as last time: done
   (an idle run is 1-2 GETs, 1 D1 read and no writes);
4. otherwise the stored folder oids (``leaderboard_forge_pulls``), and for at most ``max_pulls``
   folders whose oid changed: the folder listing (1 GET), its files (1 GET per 50 files) and, for
   branch-backed pulls without a patch, ``compare`` (1 GET);
5. each pull's contributions (opened/merged/closed PR, review credits, comments, per login and
   month) are compared with what was stored for it, and only the difference is applied to
   ``leaderboard_monthly_stats`` / ``leaderboard_open_prs``, in one D1 batch (a transaction) with
   the pull rows and the cursor. The ledger commit is saved only once every changed folder is
   read, so a run that stops at its budget is continued by the next one.

Scoring and identities match the GitHub-era rows of the same tables: rows are keyed by the GitHub
login when the roster knows one for the forge account (else the forge login), so a person's GitHub
history and forge activity add up in the leaderboard.
"""

from __future__ import annotations

import base64
import json
import re
import time
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import quote, urlencode

FORGE_URL = "https://git.owaspblt.org"
FORGE_REPO = "owasp-blt/BLT"
WEB_URL = f"{FORGE_URL}/BLT"
PULL_LEDGER = "forkmesh/pulls"
ROSTER_PATH = ".forkmesh/contributors/contributors.json"
ROSTER_MAX_AGE = 86400
BLOB_BATCH = 50
STATE_VERSION = 1
MAX_REQUESTS = 40          # of the free plan's 50 subrequests per invocation
MAX_PULLS_PER_RUN = 8      # keeps D1 statements per run well under 50
REVIEW_CREDITS_PER_PR = 2  # first two reviewers per PR and month, as on GitHub
FIELDS = ("opened_prs", "merged_prs", "closed_prs", "reviews", "comments")
MERGED = ("merged", "closed-merged")
COMMENT_TYPES = ("comment", "line-comment", "thread-comment")
EVENT_FILE = re.compile(r"^\d+-[A-Za-z0-9_-]+\.md$")
BOT_NAMES = frozenset({"owasp-blt-actions", "forkmesh", "dependabot", "github-actions", "renovate",
                       "actions-user", "coderabbitai", "coderabbit", "copilot", "sentry-autofix"})
BOT_SUFFIXES = ("[bot]", "-bot", "_bot")
EXTRA_PROJECTS = ("my-gsoc-tool", "coderabbit", "dot_github")
SHARED = "(shared)"

# (status, parsed JSON or None)
GetJson = Callable[[str], Awaitable[tuple]]


class BudgetExceeded(Exception):
    """This run has made its allowed number of forge requests."""


class ForgeError(Exception):
    """The forge answered with an error other than 404."""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_front_matter(text: Optional[str]) -> tuple:
    """(values, body) of a ``---`` front-matter document; ({}, text) without one."""
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


def to_ms(value: Any) -> int:
    """Epoch milliseconds from ms (int or digits) or an ISO time; 0 when unknown."""
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return 0
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})", str(value))
    if not match:
        return 0
    import calendar
    return int(calendar.timegm(tuple(int(g) for g in match.groups()) + (0, 0, 0))) * 1000


def month_of(ms: int) -> str:
    return time.strftime("%Y-%m", time.gmtime(ms / 1000))


def is_bot(name: Optional[str]) -> bool:
    """True for automation accounts (and for a missing author)."""
    lowered = (name or "").strip().lower()
    if not lowered:
        return True
    return lowered in BOT_NAMES or lowered.endswith(BOT_SUFFIXES) or "[bot]" in lowered


def is_counted_comment(body: str) -> bool:
    """Comments count unless they are slash commands or CodeRabbit pings (as on GitHub)."""
    text = (body or "").strip()
    if not text:
        return False
    if re.match(r"^/[A-Za-z][\w-]*(\s|$)", text):
        return False
    return "coderabbit" not in text.lower()


_DIFF_PATH = re.compile(r"^diff --git a/(\S+) b/(\S+)", re.MULTILINE)
_TITLE_PREFIX = re.compile(r"^\s*(?:\[([A-Za-z0-9_.-]+)\]|([A-Za-z0-9_.-]+)\s*:)")


def path_project(path: str) -> str:
    """The project folder a changed file belongs to (blt-hackathons' rule)."""
    parts = path.split("/")
    if len(parts) == 1:
        return SHARED
    if parts[0] == ".forkmesh" and len(parts) == 2 and "--" in parts[1]:
        return parts[1].split("--", 1)[0].lower()
    if parts[0].startswith("."):
        return SHARED
    return parts[0].lower()


def title_project(title: Optional[str]) -> str:
    match = _TITLE_PREFIX.match(title or "")
    return (match.group(1) or match.group(2)).lower() if match else ""


def pull_projects(title: Optional[str], patch_text: str) -> list:
    """Folders a pull belongs to: the folders its diff touches, else a project title prefix."""
    paths = set()
    for old, new in _DIFF_PATH.findall(patch_text or ""):
        paths.update((old, new))
    touched = sorted({path_project(p) for p in paths} - {SHARED})
    if touched:
        return touched
    prefix = title_project(title)
    if prefix and (prefix.startswith("blt-") or prefix in EXTRA_PROJECTS):
        return [prefix]
    return []


def parse_pull(number: int, pull_md: Optional[str], files: dict, patch_text: str = "") -> Optional[dict]:
    """Normalize one pull folder; None when ``pull.md`` is unreadable."""
    meta, _ = parse_front_matter(pull_md)
    if not meta:
        return None
    status = (meta.get("status") or "open").strip().lower()
    events = []
    for name in sorted(files):
        values, body = parse_front_matter(files[name])
        if not values:
            continue
        events.append({
            "type": (values.get("type") or "").strip().lower(),
            "state": (values.get("state") or "").strip().lower(),
            "author": (values.get("authorName") or "").strip(),
            "ts": to_ms(values.get("ts")),
            "body": body,
        })
    opened = to_ms(meta.get("ts"))
    newest = max([opened, to_ms(meta.get("mergedAt"))] + [e["ts"] for e in events])
    closed = to_ms(meta.get("closedAt"))
    if not closed:
        closes = [e["ts"] for e in events if e["type"] in ("close", "closed", "merge", "merged")]
        closed = max(closes) if closes else newest
    merged_at = (to_ms(meta.get("mergedAt")) or closed) if status in MERGED else 0
    return {
        "number": int(number),
        "title": (meta.get("title") or "").strip(),
        "status": status,
        "author": (meta.get("authorName") or "").strip(),
        "opened": opened,
        "merged": merged_at,
        "closed": closed if status != "open" else 0,
        "updated": newest,
        "events": events,
        "projects": pull_projects(meta.get("title"), patch_text),
        "derive": meta.get("derive", ""),
        "base": meta.get("mergeBase") or meta.get("creationBaseOid") or "",
        "head": meta.get("mergeHead") or meta.get("creationHeadOid") or "",
    }


# ---------------------------------------------------------------------------
# Identities
# ---------------------------------------------------------------------------

def compact_roster(data: Any) -> dict:
    """{lower(forge or GitHub login): [leaderboard login, name, avatar path]} from contributors.json.

    The leaderboard login is the GitHub login when known (the key of the GitHub-era rows), else
    the forge login.
    """
    people = (data or {}).get("contributors") if isinstance(data, dict) else None
    roster = {}
    for person in people or []:
        if not isinstance(person, dict):
            continue
        login, github = person.get("login") or "", person.get("github") or ""
        canonical = github or login
        if not canonical or is_bot(canonical):
            continue
        entry = [canonical, person.get("name") or canonical, person.get("avatar") or ""]
        for key in (login, github):
            if key:
                roster.setdefault(key.lower(), entry)
    return roster


def resolve(roster: dict, forge_name: str) -> str:
    """The leaderboard login of a forge account."""
    entry = (roster or {}).get((forge_name or "").lower())
    return entry[0] if entry else forge_name


def raw_url(path: str) -> str:
    return f"{FORGE_URL}/api/repo/{FORGE_REPO}/raw?path={quote(path, safe='/')}"


def person(login: str, roster: dict, forge_logins: Optional[set] = None) -> dict:
    """Display name, avatar and profile for a leaderboard login.

    Roster entries use the README avatar; otherwise forge accounts (logins seen on the forge) use
    the forge avatar and profile, and GitHub-era logins their GitHub ones.
    """
    entry = (roster or {}).get((login or "").lower())
    on_forge = (login or "").lower() in (forge_logins or set())
    forge_profile = f"{FORGE_URL}/@{login}"
    if entry:
        return {
            "name": entry[1],
            "avatar_url": raw_url(entry[2]) if entry[2] else f"{FORGE_URL}/api/accounts/{quote(login.lower())}/avatar",
            "profile_url": forge_profile if on_forge else f"https://github.com/{quote(entry[0])}",
        }
    if on_forge:
        return {"name": login, "avatar_url": f"{FORGE_URL}/api/accounts/{quote(login.lower())}/avatar",
                "profile_url": forge_profile}
    return {"name": login, "avatar_url": f"https://avatars.githubusercontent.com/{quote(login)}?size=40&v=4",
            "profile_url": f"https://github.com/{quote(login)}"}


# ---------------------------------------------------------------------------
# Contributions and deltas
# ---------------------------------------------------------------------------

def contributions(pull: Optional[dict], roster: dict) -> dict:
    """{"<month>|<login>|<field>": n, "open|<login>": 1} that one pull adds to the leaderboard.

    Opened/merged/closed PRs count for a human author; review credits go to the first two other
    humans reviewing it in a month; comments (not slash commands or CodeRabbit pings) to any human.
    """
    found: dict = {}
    if not pull or pull.get("status") == "deleted":
        return found

    def add(key: str, n: int = 1) -> None:
        found[key] = found.get(key, 0) + n

    author = resolve(roster, pull["author"]) if not is_bot(pull["author"]) else ""
    if author:
        if pull["status"] == "open":
            add(f"open|{author}")
        if pull["opened"]:
            add(f"{month_of(pull['opened'])}|{author}|opened_prs")
        if pull["status"] in MERGED and pull["merged"]:
            add(f"{month_of(pull['merged'])}|{author}|merged_prs")
        elif pull["status"] not in ("open",) + MERGED and pull["closed"]:
            add(f"{month_of(pull['closed'])}|{author}|closed_prs")
    credited: dict = {}
    for event in sorted(pull.get("events") or [], key=lambda e: e["ts"]):
        if not event["ts"] or is_bot(event["author"]):
            continue
        login = resolve(roster, event["author"])
        month = month_of(event["ts"])
        if event["type"] == "review":
            if author and login.lower() == author.lower():
                continue
            names = credited.setdefault(month, [])
            if login.lower() in names or len(names) >= REVIEW_CREDITS_PER_PR:
                continue
            names.append(login.lower())
            add(f"{month}|{login}|reviews")
        elif event["type"] in COMMENT_TYPES and is_counted_comment(event["body"]):
            add(f"{month}|{login}|comments")
    return found


def diff(old: dict, new: dict) -> dict:
    """new - old, without zero entries."""
    out = {}
    for key in set(old or {}) | set(new or {}):
        delta = int((new or {}).get(key, 0)) - int((old or {}).get(key, 0))
        if delta:
            out[key] = delta
    return out


def add_into(total: dict, delta: dict) -> None:
    for key, value in delta.items():
        total[key] = total.get(key, 0) + value
        if not total[key]:
            del total[key]


def delta_statements(org: str, delta: dict, now: int) -> list:
    """D1 upserts applying ``delta``: one per (month, login) and one per open-PR login."""
    monthly: dict = {}
    opens: dict = {}
    for key, value in sorted(delta.items()):
        parts = key.split("|")
        if parts[0] == "open" and len(parts) == 2:
            opens[parts[1]] = opens.get(parts[1], 0) + value
        elif len(parts) == 3 and parts[2] in FIELDS:
            monthly.setdefault((parts[0], parts[1]), {})[parts[2]] = value
    statements = []
    for (month, login), fields in sorted(monthly.items()):
        values = [int(fields.get(f, 0)) for f in FIELDS]
        updates = ", ".join(
            f"{f} = MAX(0, leaderboard_monthly_stats.{f} + ?)" for f in FIELDS
        )
        statements.append((
            f"INSERT INTO leaderboard_monthly_stats (org, month_key, user_login, {', '.join(FIELDS)}, updated_at) "
            f"VALUES (?, ?, ?, {', '.join('MAX(0, ?)' for _ in FIELDS)}, ?) "
            f"ON CONFLICT(org, month_key, user_login) DO UPDATE SET {updates}, updated_at = excluded.updated_at",
            (org, month, login, *values, now, *values),
        ))
    for login, value in sorted(opens.items()):
        if value:
            statements.append((
                "INSERT INTO leaderboard_open_prs (org, user_login, open_prs, updated_at) VALUES (?, ?, MAX(0, ?), ?) "
                "ON CONFLICT(org, user_login) DO UPDATE SET "
                "open_prs = MAX(0, leaderboard_open_prs.open_prs + ?), updated_at = excluded.updated_at",
                (org, login, value, now, value),
            ))
    return statements


# ---------------------------------------------------------------------------
# Forge client
# ---------------------------------------------------------------------------

def blob_text(blob: Any) -> Optional[str]:
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


class ForgeClient:
    """Counted anonymous GETs against ``{url}/api/repo/owasp-blt/BLT/``."""

    def __init__(self, get_json: GetJson, url: str = FORGE_URL, repo: str = FORGE_REPO,
                 max_requests: int = MAX_REQUESTS):
        self._get_json = get_json
        self.api = f"{url.rstrip('/')}/api/repo/{repo}"
        self.max_requests = max_requests
        self.requests = 0

    def remaining(self) -> int:
        return self.max_requests - self.requests

    async def get(self, operation: str, params: Optional[list] = None) -> Any:
        """The JSON answer, or None for 404."""
        if self.requests >= self.max_requests:
            raise BudgetExceeded()
        self.requests += 1
        query = urlencode(params or [])
        status, data = await self._get_json(f"{self.api}/{operation}" + (f"?{query}" if query else ""))
        if status == 404:
            return None
        if status >= 400 or not isinstance(data, dict):
            raise ForgeError(f"{operation} answered {status}")
        return data

    async def tree(self, path: str, ref: str = "") -> Any:
        return await self.get("tree", [("path", path)] + ([("ref", ref)] if ref else []))

    async def blobs(self, paths: list, ref: str = "") -> dict:
        found = {}
        for start in range(0, len(paths), BLOB_BATCH):
            chunk = paths[start:start + BLOB_BATCH]
            data = await self.get("blobs", [("path", p) for p in chunk] + ([("ref", ref)] if ref else []))
            for path in chunk:
                found[path] = blob_text(((data or {}).get("blobs") or {}).get(path))
        return found


def numbered_dirs(tree: Any) -> dict:
    found = {}
    for entry in (tree or {}).get("entries") or []:
        name = str(entry.get("name") or "")
        if entry.get("type") == "tree" and name.isdigit():
            found[name] = str(entry.get("oid") or "")
    return found


async def read_pull(client: ForgeClient, number: str, ref: str) -> Optional[dict]:
    """Read one pull folder at a ledger commit (or its own pull ref)."""
    folder = f".forkmesh/pulls/{number}"
    listing = await client.tree(folder, ref)
    names = [str(e.get("name") or "") for e in (listing or {}).get("entries") or [] if e.get("type") == "blob"]
    wanted = ["pull.md"] + [n for n in names if EVENT_FILE.match(n)]
    wanted += [n for n in ("changes.patch", "commits.mbox") if n in names]
    texts = await client.blobs([f"{folder}/{n}" for n in wanted], ref)
    pull_md = texts.get(f"{folder}/pull.md")
    events = {n: texts.get(f"{folder}/{n}") for n in wanted if n != "pull.md" and n.endswith(".md")}
    patch = (texts.get(f"{folder}/changes.patch") or "") + (texts.get(f"{folder}/commits.mbox") or "")
    pull = parse_pull(int(number), pull_md, events, patch)
    if pull and not pull["projects"] and not patch and pull["derive"] == "branch" and pull["base"] and pull["head"]:
        compared = await client.get("compare", [("base", pull["base"]), ("head", pull["head"])]) or {}
        pull["projects"] = pull_projects(pull["title"], compared.get("commits") or compared.get("patch") or "")
    return pull


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def new_state() -> dict:
    return {"v": STATE_VERSION, "ledger_commit": "", "roster": {}, "roster_at": 0, "forge_logins": []}


async def load_state(store, org: str) -> tuple:
    """(state, raw JSON text) of the cursor row; a fresh state when there is none."""
    rows = await store.all("SELECT state FROM leaderboard_forge_cursor WHERE org = ?", (org,))
    text = (rows[0].get("state") if rows else "") or ""
    try:
        state = json.loads(text) if text else {}
    except ValueError:
        state = {}
    if not isinstance(state, dict) or state.get("v") != STATE_VERSION:
        state = new_state()
    return state, text


def _state_json(state: dict) -> str:
    return json.dumps(state, sort_keys=True, separators=(",", ":"))


async def sync(client: ForgeClient, store, org: str, now: Optional[int] = None,
               max_pulls: int = MAX_PULLS_PER_RUN) -> dict:
    """One incremental run. ``store`` has ``all(sql, params)`` and ``batch([(sql, params)])``."""
    now = int(now if now is not None else time.time())
    state, stored_text = await load_state(store, org)
    summary = {"ok": True, "ledger": "unknown", "pulls_read": 0, "pulls_removed": 0, "pending": 0,
               "statements": 0, "requests": 0}

    try:
        if now - int(state.get("roster_at") or 0) >= ROSTER_MAX_AGE:
            data = await client.get("raw", [("path", ROSTER_PATH)])
            roster = compact_roster(data)
            if roster:
                state["roster"] = roster
            state["roster_at"] = now
    except BudgetExceeded:
        pass
    except ForgeError as exc:
        summary["roster_error"] = str(exc)
        state["roster_at"] = now - ROSTER_MAX_AGE + 3600  # retry in an hour
    roster = state.get("roster") or {}

    statements: list = []
    tree = await client.tree(".forkmesh/pulls", PULL_LEDGER)
    if tree is None:
        summary["ledger"] = "missing"  # no ledger branch yet: no pull requests
    else:
        summary["ledger"] = "ok"
        commit = str(tree.get("commit") or "")
        if not commit or commit != state.get("ledger_commit"):
            statements, done = await _sync_pulls(client, store, org, tree, state, roster, now, max_pulls, summary)
            if done:
                state["ledger_commit"] = commit

    text = _state_json(state)
    if text != stored_text:
        statements.append((
            "INSERT INTO leaderboard_forge_cursor (org, ledger_commit, state, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(org) DO UPDATE SET ledger_commit = excluded.ledger_commit, state = excluded.state, "
            "updated_at = excluded.updated_at",
            (org, str(state.get("ledger_commit") or ""), text, now),
        ))
    if statements:
        await store.batch(statements)
    summary["statements"] = len(statements)
    summary["requests"] = client.requests
    return summary


async def _sync_pulls(client, store, org, tree, state, roster, now, max_pulls, summary) -> tuple:
    commit = str(tree.get("commit") or "")
    listed = {n: (oid, commit) for n, oid in numbered_dirs(tree).items()}
    for number, ref in (tree.get("pullRefs") or {}).items():
        if str(number).isdigit() and str(number) not in listed and ref:
            listed[str(number)] = (f"ref:{ref}", str(ref))

    known_rows = await store.all("SELECT pr_number, oid FROM leaderboard_forge_pulls WHERE org = ?", (org,))
    known = {str(int(r.get("pr_number"))): str(r.get("oid") or "") for r in known_rows}
    stale = sorted((n for n, (oid, _) in listed.items() if known.get(n) != oid), key=int)
    # A pull folder that disappeared takes its contributions with it; an empty listing next to
    # stored pulls is treated as a bad answer rather than a wipe.
    removed = sorted((n for n in known if n not in listed), key=int) if listed else []
    batch = stale[:max_pulls]

    old_contrib = {}
    touched = batch + removed
    for start in range(0, len(touched), 50):
        chunk = touched[start:start + 50]
        if not chunk:
            continue
        rows = await store.all(
            f"SELECT pr_number, contrib FROM leaderboard_forge_pulls WHERE org = ? AND pr_number IN "
            f"({', '.join('?' for _ in chunk)})",
            (org, *[int(n) for n in chunk]),
        )
        for row in rows:
            try:
                old_contrib[str(int(row.get("pr_number")))] = json.loads(row.get("contrib") or "{}")
            except ValueError:
                old_contrib[str(int(row.get("pr_number")))] = {}

    total: dict = {}
    rows_out: list = []
    forge_logins = set(state.get("forge_logins") or [])
    read = 0
    for number in batch:
        oid, ref = listed[number]
        try:
            pull = await read_pull(client, number, ref)
        except BudgetExceeded:
            break
        read += 1
        new = contributions(pull, roster)
        add_into(total, diff(old_contrib.get(number, {}), new))
        for key in new:
            forge_logins.add(key.split("|")[1].lower())
        p = pull or {}
        author = resolve(roster, p.get("author", "")) if p and not is_bot(p.get("author")) else (p.get("author") or "")
        rows_out.append((
            "INSERT INTO leaderboard_forge_pulls (org, pr_number, oid, author_login, status, title, projects, "
            "opened_at, merged_at, closed_at, contrib, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(org, pr_number) DO UPDATE SET oid = excluded.oid, author_login = excluded.author_login, "
            "status = excluded.status, title = excluded.title, projects = excluded.projects, "
            "opened_at = excluded.opened_at, merged_at = excluded.merged_at, closed_at = excluded.closed_at, "
            "contrib = excluded.contrib, updated_at = excluded.updated_at",
            (org, int(number), oid, author, p.get("status", "unreadable"), (p.get("title") or "")[:200],
             ",".join(p.get("projects") or []), int(p.get("opened", 0)) // 1000, int(p.get("merged", 0)) // 1000,
             int(p.get("closed", 0)) // 1000, json.dumps(new, sort_keys=True, separators=(",", ":")),
             int(p.get("updated", 0)) // 1000 or now),
        ))
    for number in removed:
        add_into(total, diff(old_contrib.get(number, {}), {}))
        rows_out.append(("DELETE FROM leaderboard_forge_pulls WHERE org = ? AND pr_number = ?", (org, int(number))))
    state["forge_logins"] = sorted(forge_logins)
    summary.update(pulls_read=read, pulls_removed=len(removed), pending=len(stale) - read)
    return delta_statements(org, total, now) + rows_out, read == len(stale)


# ---------------------------------------------------------------------------
# Leaderboard rows
# ---------------------------------------------------------------------------

def merge_rows(monthly_rows: list, open_rows: list, roster: Optional[dict] = None) -> dict:
    """Per-person stats from monthly and open-PR rows, logins compared case-insensitively.

    GitHub logins and forge logins of the same person share a row key (the roster maps forge
    accounts to GitHub logins), and differently-cased spellings of one login are added up.
    """
    roster = roster or {}
    users: dict = {}
    names: dict = {}

    def ensure(login: str) -> dict:
        key = login.lower()
        entry = roster.get(key)
        names.setdefault(key, entry[0] if entry else login)
        if key not in users:
            users[key] = {"openPrs": 0, "openedPrs": 0, "mergedPrs": 0, "closedPrs": 0,
                          "reviews": 0, "comments": 0, "total": 0}
        return users[key]

    for row in monthly_rows or []:
        login = row.get("user_login")
        if not login:
            continue
        stats = ensure(login)
        stats["openedPrs"] += int(row.get("opened_prs") or 0)
        stats["mergedPrs"] += int(row.get("merged_prs") or 0)
        stats["closedPrs"] += int(row.get("closed_prs") or 0)
        stats["reviews"] += int(row.get("reviews") or 0)
        stats["comments"] += int(row.get("comments") or 0)
    for row in open_rows or []:
        login = row.get("user_login")
        if not login:
            continue
        ensure(login)["openPrs"] += int(row.get("open_prs") or 0)

    result = {}
    for key, s in users.items():
        s["total"] = s["openPrs"] + s["mergedPrs"] * 10 - s["closedPrs"] * 2 + s["reviews"] * 5 + s["comments"] * 2
        result[names[key]] = s
    return result
