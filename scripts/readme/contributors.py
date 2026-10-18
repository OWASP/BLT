#!/usr/bin/env python3
"""Everyone who contributed to a BLT project, for the README contributor wall.

Reads every commit (authors and Co-authored-by trailers) in this repository, which holds the full
history of each project, and turns the commit identities (name + email) into people:

  1. scripts/readme/contributor-logins.tsv   manual email -> account mappings
  2. noreply addresses                        <id>+<login>@users.noreply.github.com,
                                              <id>-<user>@users.noreply.gitlab.com
  3. blt-gsoc/data/contributors.json          GSoC contributors with their commit author names
  4. known GitHub logins                      a name or email local part equal to a login seen above
                                              or in blt-waypoint/public/github_data.json
  5. GitHub commit search by author email     (network, a few per run, cached)
  6. git.owaspblt.org pull and issue authors  the forkmesh/pulls and .forkmesh/issues ledgers
                                              (scripts/forkmesh/ledger.py), matched by name (cached)

Identities are merged into one person when they share an email, an account, a GitHub user id or a
full name. Bots and placeholder identities are left out; people without any account are kept by name
with a generated identicon. Anyone whose login also has an account on git.owaspblt.org links there.

Output, all under .forkmesh/contributors/:
  <slug>.png          64x64 avatar (re-downloaded when older than AVATAR_MAX_AGE_DAYS)
  contributors.json   one entry per person
  lookups.json        cache of network lookups (emails stored as hashes)

Network failures never fail the run: old files and cached answers are kept.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from io import BytesIO

ROOT = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
).stdout.strip()
OUT_DIR = os.path.join(ROOT, ".forkmesh", "contributors")
OUT_REL = ".forkmesh/contributors"
LOGINS = os.path.join(ROOT, "scripts", "readme", "contributor-logins.tsv")
ROUTES = os.path.join(ROOT, "scripts", "routing", "projects.tsv")
GSOC = os.path.join(ROOT, "blt-gsoc", "data", "contributors.json")
WAYPOINT = os.path.join(ROOT, "blt-waypoint", "public", "github_data.json")
INSTANCE = "https://git.owaspblt.org"

AVATAR_SIZE = 64
AVATAR_MAX_AGE_DAYS = int(os.environ.get("CONTRIBUTOR_AVATAR_DAYS", "30"))
AVATAR_REFRESH_PER_RUN = int(os.environ.get("CONTRIBUTOR_AVATAR_REFRESH", "60"))
AVATAR_RETRY_DAYS = 7          # retry a failed avatar download after this many days
INSTANCE_RECHECK_DAYS = 7      # re-check git.owaspblt.org accounts
FORGE_RECHECK_DAYS = 1         # re-read the git.owaspblt.org pull and issue ledgers
SEARCH_NEGATIVE_DAYS = 90      # re-try a GitHub email search that found nothing
GH_TOKEN = os.environ.get("GH_API_TOKEN", "").strip()
# GitHub API calls per run: commit searches (30/min with a token, 10/min without) and user lookups
GITHUB_BUDGET = int(os.environ.get("CONTRIBUTOR_GITHUB_LOOKUPS", "40" if GH_TOKEN else "8"))
UA = {"User-Agent": "owasp-blt-readme"}

GH_NOREPLY = re.compile(r"^(?:(\d+)\+)?([a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\[bot\])?)@users\.noreply\.github\.com$", re.I)
GL_NOREPLY = re.compile(r"^\d+-([a-z0-9_.-]+)@users\.noreply\.gitlab\.com$", re.I)
INSTANCE_NOREPLY = re.compile(r"^([a-z0-9_.-]+)@users\.noreply\.git\.owaspblt\.org$", re.I)
BOT = re.compile(
    r"\[bot\]|dependabot|github-actions|^github action$|^action@github\.com$|actions-user|renovate|"
    r"pre-commit-ci|coderabbit|forkmesh|owasp-blt-actions|copilot|^claude\b|anthropic\.com|cursor|"
    r"commandcode|sentry|seer-by|cloudflare-workers|web-flow|bugheist-bot|codex|^owasp blt$|\bbot$|"
    r"service_account|^ghost user$",
    re.I,
)
PLACEHOLDERS = {"your name", "root", "author name", "[author name]", "name", "you@example.com"}


def today():
    return date.today().isoformat()


def older_than(day, days):
    if not day:
        return True
    try:
        return date.fromisoformat(day) < date.today() - timedelta(days=days)
    except ValueError:
        return True


def norm(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower())


def email_hash(email):
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]


def log(msg):
    print(f"contributors: {msg}", file=sys.stderr)


# ---------------------------------------------------------------- network helpers

_session = None


def http():
    global _session
    if _session is None:
        import requests

        _session = requests.Session()
        _session.headers.update(UA)
    return _session


def get(url, **kw):
    """GET that never raises: returns a response or None."""
    try:
        return http().get(url, timeout=kw.pop("timeout", 20), **kw)
    except Exception as exc:  # network errors, missing requests module
        log(f"GET {url.split('?')[0]} failed: {exc}")
        return None


class GitHub:
    def __init__(self, budget):
        self.budget = budget
        self.stopped = False
        self.last = 0.0

    def call(self, path, params=None, search=False):
        if self.stopped or self.budget <= 0:
            return None
        self.budget -= 1
        gap = (2.1 if GH_TOKEN else 6.5) if search else 0.2
        time.sleep(max(0.0, self.last + gap - time.time()))
        self.last = time.time()
        headers = {"Accept": "application/vnd.github+json"}
        if GH_TOKEN:
            headers["Authorization"] = f"Bearer {GH_TOKEN}"
        resp = get(f"https://api.github.com{path}", params=params, headers=headers)
        if resp is None:
            return None
        if resp.status_code in (403, 429):
            log(f"GitHub API limit reached ({resp.status_code}); stopping lookups for this run")
            self.stopped = True
            return None
        return resp


# ---------------------------------------------------------------- inputs


def display_names():
    names = {}
    for line in open(ROUTES, encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            folder, display = line.rstrip("\n").split("\t")[:2]
            if folder != "-":
                names[folder] = display
    return names


def load_overrides():
    """email -> ("github"|"gitlab"|"instance"|"git"|"bot", value)."""
    out = {}
    if not os.path.exists(LOGINS):
        return out
    for line in open(LOGINS, encoding="utf-8"):
        if line.startswith("#") or "\t" not in line:
            continue
        email, value = (x.strip() for x in line.rstrip("\n").split("\t", 1))
        if value == "-":
            out[email.lower()] = ("git", None)
        elif value == "bot":
            out[email.lower()] = ("bot", None)
        elif ":" in value:
            kind, _, val = value.partition(":")
            out[email.lower()] = (kind.strip(), val.strip())
        else:
            out[email.lower()] = ("github", value)
    return out


def load_gsoc():
    """norm(commit author name or email local part) -> GitHub login, plus GitLab usernames."""
    aliases, gitlab = {}, {}
    try:
        for c in json.load(open(GSOC, encoding="utf-8")):
            login = (c.get("github") or "").strip()
            if not login:
                continue
            for alias in [c.get("name")] + (c.get("commit_authors") or []):
                if alias and len(norm(alias)) >= 4:
                    aliases[norm(alias)] = login
            if c.get("gitlab"):
                gitlab[login.lower()] = c["gitlab"]
    except (OSError, ValueError):
        pass
    return aliases, gitlab


def waypoint_logins():
    try:
        data = json.load(open(WAYPOINT, encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {c["login"] for r in data.get("repos", []) for c in (r.get("contributors") or [])
            if c.get("login") and c["login"] != "ghost"}


def read_commits(names):
    """Yield (identity name, email, timestamp, project) for every commit author and co-author."""
    out = subprocess.run(
        ["git", "-C", ROOT, "log", "--no-merges", "--name-only",
         "--format=%x00%H%x1f%aN%x1f%aE%x1f%at%x1f%(trailers:key=Co-authored-by,valueonly,separator=%x1e)",
         "HEAD"],
        capture_output=True, text=True, check=True, errors="replace",
    ).stdout
    for chunk in out.split("\0")[1:]:
        head, _, files = chunk.partition("\n")
        sha, name, email, ts, trailers = (head.split("\x1f") + [""] * 5)[:5]
        folders = {f.split("/", 1)[0] for f in files.split("\n") if "/" in f}
        projects = sorted({names.get(f, "BLT") for f in folders if not f.startswith(".") or f == ".forkmesh"} or {"BLT"})
        people = [(name.strip(), email.strip())]
        for t in trailers.split("\x1e"):
            m = re.match(r"\s*(.+?)\s*<([^>]+)>\s*$", t)
            if m:
                people.append((m.group(1), m.group(2)))
        seen = set()
        for n, e in people:
            if (n.lower(), e.lower()) not in seen:
                seen.add((n.lower(), e.lower()))
                yield sha, n, e, int(ts or 0), projects


def is_bot(name, email):
    name_l, email_l = name.lower().strip(), email.lower().strip()
    if name_l in PLACEHOLDERS or email_l in PLACEHOLDERS or not name_l:
        return True
    return bool(BOT.search(name_l) or BOT.search(email_l))


# ---------------------------------------------------------------- grouping


class Identity:
    __slots__ = ("name", "email", "raw", "commits", "first", "last", "projects", "github", "gh_id", "gitlab",
                 "forced_git", "former")

    def __init__(self, name, email):
        self.name, self.email, self.raw = name, email.lower(), email
        self.commits, self.first, self.last = set(), None, None
        self.projects = Counter()
        self.github = self.gh_id = self.gitlab = self.former = None
        self.forced_git = False


def collect():
    names = display_names()
    idents = {}
    for sha, name, email, ts, projects in read_commits(names):
        if is_bot(name, email):
            continue
        key = (name, email.lower())
        ident = idents.get(key) or idents.setdefault(key, Identity(name, email))
        if sha in ident.commits:
            continue
        ident.commits.add(sha)
        ident.first = ts if ident.first is None else min(ident.first, ts)
        ident.last = ts if ident.last is None else max(ident.last, ts)
        ident.projects.update(projects)
    return list(idents.values())


def resolve(idents, cache, overrides, gsoc_aliases, known_logins):
    """Attach accounts to identities from offline sources and the lookup cache."""
    searched = cache.setdefault("github_email", {})
    for ident in idents:
        ident.github = ident.gh_id = ident.gitlab = ident.former = None
        ident.forced_git = False
        email = ident.raw
        kind, val = overrides.get(ident.email, (None, None))
        if kind == "github":
            ident.github = val
        elif kind == "gitlab":
            ident.gitlab = val
        elif kind == "instance":
            ident.github = val
        elif kind == "git":
            ident.forced_git = True
            continue
        m = GH_NOREPLY.match(email)
        if m and not ident.github:
            ident.gh_id, ident.github = m.group(1), m.group(2)
        m = GL_NOREPLY.match(email)
        if m and not ident.gitlab:
            ident.gitlab = m.group(1)
        m = INSTANCE_NOREPLY.match(email)
        if m and not ident.github:
            ident.github = m.group(1)
        if not ident.github:
            hit = searched.get(email_hash(email))
            if hit and hit.get("login"):
                ident.github = hit["login"]
    canonical(idents, cache)
    logins = {l for l in known_logins} | {i.github for i in idents if i.github}
    by_norm = defaultdict(set)
    for login in logins:
        by_norm[norm(login)].add(login)
    for ident in idents:
        if ident.github or ident.gitlab or ident.forced_git:
            continue
        local = ident.email.split("@")[0]
        for key in (norm(ident.name), norm(local)):
            if key in gsoc_aliases:
                ident.github = gsoc_aliases[key]
                break
            if len(key) >= 4 and len(by_norm.get(key, ())) == 1:
                ident.github = next(iter(by_norm[key]))
                break
    canonical(idents, cache)


def canonical(idents, cache):
    """Use GitHub user ids (from noreply emails and avatar redirects) to follow renamed accounts.

    A login whose github.com/<login>.png is gone and whose id has no current login is a deleted
    account: the identity keeps it as `former` and is listed without a profile."""
    checked = cache.get("github_login", {})
    current = {str(e["id"]): e["login"] for e in checked.values() if e.get("id")}
    for gid, e in cache.get("github_id", {}).items():
        if e.get("login"):
            current.setdefault(gid, e["login"])
    for ident in idents:
        if not ident.github:
            continue
        e = checked.get(ident.github.lower())
        if e and e.get("id") and not ident.gh_id:
            ident.gh_id = str(e["id"])
        if ident.gh_id and ident.gh_id in current:
            ident.github = current[ident.gh_id]
        elif e and e.get("gone"):
            ident.former, ident.github = ident.github, None
            ident.forced_git = True


def full_name_key(name):
    words = [w for w in re.split(r"\s+", name.strip()) if norm(w)]
    key = norm(name)
    return key if len(words) >= 2 and len(key) >= 6 and "\\" not in name else None


def group(idents):
    parent = list(range(len(idents)))
    accounts = [({i.github.lower()} if i.github else set()) for i in idents]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b, strict=False):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if strict and accounts[ra] and accounts[rb] and accounts[ra] != accounts[rb]:
            return
        parent[rb] = ra
        accounts[ra] |= accounts[rb]

    def link(keyfunc, strict=False):
        first = {}
        for n, ident in enumerate(idents):
            key = keyfunc(ident)
            if key is None:
                continue
            if key in first:
                union(first[key], n, strict)
            else:
                first[key] = n

    link(lambda i: i.email)
    link(lambda i: ("gh", i.github.lower()) if i.github else None)
    link(lambda i: ("id", i.gh_id) if i.gh_id else None)
    link(lambda i: ("gl", i.gitlab.lower()) if i.gitlab else None)
    link(lambda i: full_name_key(i.name), strict=True)
    # a name that equals someone's login ("Sarthak5598") joins that person
    login_of = {norm(i.github): n for n, i in enumerate(idents) if i.github}
    for n, ident in enumerate(idents):
        key = norm(ident.name)
        if len(key) >= 4 and key in login_of:
            union(login_of[key], n, strict=True)
    groups = defaultdict(list)
    for n, ident in enumerate(idents):
        groups[find(n)].append(ident)
    return list(groups.values())


def summarize(members):
    weight, ids, former = Counter(), Counter(), set()
    github, gitlab, names = Counter(), Counter(), Counter()
    commits, first, last, projects = set(), None, None, Counter()
    for i in members:
        n = len(i.commits)
        commits |= i.commits
        first = i.first if first is None else min(first, i.first)
        last = i.last if last is None else max(last, i.last)
        projects.update(i.projects)
        if i.github:
            github[i.github] += n + (0.5 if i.gh_id else 0)
            if i.gh_id:
                ids[i.gh_id] += n
        if i.former:
            former.add(i.former)
        if i.gitlab:
            gitlab[i.gitlab] += n
        if "\\" not in i.name:
            names[i.name] += n
        weight[i.email] += n
    login = github.most_common(1)[0][0] if github else None
    gl = gitlab.most_common(1)[0][0] if gitlab else None
    # display name: the most used name with a space in it, else the most used name, else the login
    spaced = [n for n, _ in names.most_common() if " " in n.strip()]
    name = (spaced or [n for n, _ in names.most_common()] or [login or gl or "?"])[0]
    return {
        "name": name.strip(),
        "github": login,
        "github_id": ids.most_common(1)[0][0] if ids and login else None,
        "former": sorted(former),
        "gitlab": gl,
        "commits": len(commits),
        "first": datetime.fromtimestamp(first, timezone.utc).date().isoformat(),
        "last": datetime.fromtimestamp(last, timezone.utc).date().isoformat(),
        "projects": [p for p, _ in sorted(projects.items(), key=lambda kv: (-kv[1], kv[0]))],
        "emails": [e for e, _ in weight.most_common()],
        "names": [n for n, _ in names.most_common()],
    }


# ---------------------------------------------------------------- network lookups


def searchable(email):
    domain = email.rsplit("@", 1)[-1]
    return ("." in domain and not domain.endswith((".local", ".localdomain", "example.com", ".lan"))
            and "noreply" not in domain)


def github_lookups(people, cache, gh):
    """Commit search by author email for people without an account; current login for renamed ids."""
    searched = cache.setdefault("github_email", {})
    todo = []
    for p in people:
        if p["github"] or p["gitlab"]:
            continue
        for email in p["emails"]:
            hit = searched.get(email_hash(email))
            if searchable(email) and (hit is None or (not hit.get("login") and older_than(hit.get("checked"), SEARCH_NEGATIVE_DAYS))):
                todo.append((p["commits"], email))
    todo.sort(reverse=True)
    done = 0
    for _, email in todo:
        resp = gh.call("/search/commits", {"q": f'author-email:"{email}"', "per_page": 10}, search=True)
        if resp is None:
            break
        found = None
        if resp.status_code == 200:
            logins = Counter(item["author"]["login"] for item in resp.json().get("items", [])
                             if item.get("author") and item["author"].get("login")
                             and item["author"].get("type") == "User")
            found = logins.most_common(1)[0][0] if logins else None
        elif resp.status_code != 422:
            continue
        searched[email_hash(email)] = {"login": found, "checked": today()}
        done += 1
    if todo:
        log(f"GitHub email search: {done} of {len(todo)} pending emails looked up this run")


def check_logins(idents, cache):
    """login -> GitHub user id, read from the github.com/<login>.png redirect (not API-limited)."""
    checked = cache.setdefault("github_login", {})
    logins = {i.github for i in idents if i.github} | {i.former for i in idents if i.former}
    todo = sorted(l for l in logins if older_than(checked.get(l.lower(), {}).get("checked"), 30))

    def check(login):
        try:
            resp = http().get(f"https://github.com/{login}.png", allow_redirects=False, timeout=15)
        except Exception:
            return login, None
        m = re.search(r"/u/(\d+)", resp.headers.get("location", ""))
        if resp.status_code in (301, 302) and m:
            return login, {"login": login, "id": int(m.group(1)), "checked": today()}
        if resp.status_code == 404:
            return login, {"login": login, "id": None, "gone": True, "checked": today()}
        return login, None

    with ThreadPoolExecutor(8) as pool:
        for login, result in pool.map(check, todo):
            if result:
                checked[login.lower()] = result
    if todo:
        log(f"GitHub logins: {len(todo)} checked")


def github_ids(idents, cache, gh):
    """Current login for noreply ids whose login no longer exists (renamed accounts), via the API."""
    ids = cache.setdefault("github_id", {})
    have = {str(e["id"]) for e in cache.get("github_login", {}).values() if e.get("id")}
    for gid in sorted({i.gh_id for i in idents if i.gh_id and GH_NOREPLY.match(i.raw)} - have):
        if not older_than(ids.get(gid, {}).get("checked"), 30):
            continue
        resp = gh.call(f"/user/{gid}")
        if resp is not None and resp.status_code == 200:
            ids[gid] = {"login": resp.json().get("login"), "checked": today()}
        elif resp is not None and resp.status_code == 404:
            ids[gid] = {"login": None, "checked": today()}


def forge_authors(cache, offline):
    """norm(account name) -> {account names} of pull request and issue authors on git.owaspblt.org.

    Read from the public ledgers (anonymous /pulls and /issues answer 401), at most daily.
    """
    cache.pop("gitlab", None)  # the closed gitlab.com group's merge request authors
    entry = cache.setdefault("forge", {})
    if not offline and older_than(entry.get("checked"), FORGE_RECHECK_DAYS):
        try:
            sys.path.insert(0, os.path.join(ROOT, "scripts", "forkmesh"))
            import ledger
            client = ledger.client(seconds=120)
            names = {p.get("authorName") for p in ledger.pulls(client)}
            for issue in ledger.issues(client):
                names.add(issue.get("authorName"))
                names.update(c.get("authorName") for c in ledger.comments(issue))
            names = sorted(n for n in names if n and not is_bot(n, n))
            entry.update({"checked": today(), "authors": names})
        except Exception as exc:  # network trouble keeps the cached answer
            log(f"could not read the git.owaspblt.org ledgers: {exc}")
    index = defaultdict(set)
    for name in entry.get("authors") or []:
        index[norm(name)].add(name)
    return index


def instance_accounts(people, cache, offline):
    """login.lower() -> account name (with case) for logins that exist on git.owaspblt.org."""
    known = cache.setdefault("instance", {})
    names = sorted({(p.get("forge") or p["github"] or p["gitlab"]).lower()
                    for p in people if p.get("forge") or p["github"] or p["gitlab"]})

    def check(name):
        resp = get(f"{INSTANCE}/api/accounts/{name}", timeout=15)
        if resp is None or resp.status_code != 200:
            return name, None
        try:
            d = resp.json()
        except ValueError:
            return name, None
        exists = bool(d.get("exists") and d.get("avatarPng"))
        return name, {"exists": exists, "name": d.get("nameCase") or d.get("name") or name, "checked": today()}

    todo = [n for n in names if older_than(known.get(n, {}).get("checked"), INSTANCE_RECHECK_DAYS)]
    if todo and not offline:
        with ThreadPoolExecutor(6) as pool:
            for name, result in pool.map(check, todo):
                if result:
                    known[name] = result if result["exists"] else {"exists": False, "checked": result["checked"]}
    return {n: v["name"] for n, v in known.items() if v.get("exists")}


# ---------------------------------------------------------------- avatars


def identicon(seed):
    from PIL import Image, ImageDraw

    digest = hashlib.md5(seed.encode()).digest()
    hue = digest[0] / 255
    import colorsys

    r, g, b = (int(c * 255) for c in colorsys.hls_to_rgb(hue, 0.55, 0.55))
    img = Image.new("RGB", (AVATAR_SIZE, AVATAR_SIZE), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    cell, margin = 10, 7
    for row in range(5):
        for col in range(3):
            if digest[1 + row * 3 + col] % 2:
                for c in {col, 4 - col}:
                    x, y = margin + c * cell, margin + row * cell
                    draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(r, g, b))
    return img


def to_png(img):
    from PIL import Image, ImageOps

    img = ImageOps.exif_transpose(img)
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if has_alpha else "RGB")
    if img.size != (AVATAR_SIZE, AVATAR_SIZE):
        img = ImageOps.fit(img, (AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    img = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE if has_alpha else Image.Quantize.MEDIANCUT)
    buf = BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def write_if_changed(path, data):
    try:
        if open(path, "rb").read() == data:
            return
    except OSError:
        pass
    with open(path, "wb") as f:
        f.write(data)


def fetch_avatar(url):
    from PIL import Image

    resp = get(url, timeout=20)
    if resp is None or resp.status_code != 200 or not resp.content:
        return None
    try:
        return to_png(Image.open(BytesIO(resp.content)))
    except Exception as exc:
        log(f"could not read avatar {url.split('?')[0]}: {exc}")
        return None


def avatar_url(p):
    if p["source"] == "instance":
        return f"{INSTANCE}/api/accounts/{p['login'].lower()}/avatar"
    if p["source"] == "github":
        if p.get("github_id"):
            return f"https://avatars.githubusercontent.com/u/{p['github_id']}?s={AVATAR_SIZE}&v=4"
        return f"https://github.com/{p['login']}.png?size={AVATAR_SIZE}"
    return None


def update_avatars(people, previous, offline):
    try:
        import PIL  # noqa: F401
    except ImportError:
        log("Pillow is not installed; avatars are not updated")
        for p in people:
            old = previous.get(p["slug"], {})
            p["avatar_kind"], p["avatar_checked"] = old.get("avatar_kind"), old.get("avatar_checked")
        return
    jobs = []
    stale_budget = AVATAR_REFRESH_PER_RUN
    for p in sorted(people, key=lambda p: (previous.get(p["slug"], {}).get("avatar_checked") or "")):
        path = os.path.join(OUT_DIR, f"{p['slug']}.png")
        old = previous.get(p["slug"], {})
        p["avatar_kind"], p["avatar_checked"] = old.get("avatar_kind"), old.get("avatar_checked")
        url = avatar_url(p)
        exists = os.path.exists(path)
        if not url:
            if not exists or p["avatar_kind"] != "identicon":
                write_if_changed(path, to_png(identicon(p["slug"])))
            p["avatar_kind"], p["avatar_checked"] = "identicon", None
            continue
        if offline:
            due = False
        elif not exists or old.get("source") != p["source"]:
            due = True
        elif p["avatar_kind"] == "identicon":
            due = older_than(p["avatar_checked"], AVATAR_RETRY_DAYS)
        else:
            due = older_than(p["avatar_checked"], AVATAR_MAX_AGE_DAYS) and stale_budget > 0
            stale_budget -= due
        if due:
            jobs.append((p, path, url))
        elif not exists:
            write_if_changed(path, to_png(identicon(p["slug"])))
            p["avatar_kind"] = "identicon"

    def run(job):
        p, path, url = job
        return job, fetch_avatar(url)

    failed = 0
    with ThreadPoolExecutor(8) as pool:
        for (p, path, url), data in pool.map(run, jobs):
            if data:
                write_if_changed(path, data)
                p["avatar_kind"] = "downloaded"
            else:
                failed += 1
                if not os.path.exists(path):
                    write_if_changed(path, to_png(identicon(p["slug"])))
                    p["avatar_kind"] = "identicon"
            p["avatar_checked"] = today()
    if jobs:
        log(f"avatars: {len(jobs) - failed} downloaded, {failed} failed (kept old file or identicon)")


# ---------------------------------------------------------------- main entry


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "contributor"


def load_json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def build(offline=False):
    """Refresh .forkmesh/contributors and return the list of people, most commits first."""
    os.makedirs(OUT_DIR, exist_ok=True)
    cache_path = os.path.join(OUT_DIR, "lookups.json")
    json_path = os.path.join(OUT_DIR, "contributors.json")
    cache = load_json(cache_path, {})
    previous = {p["slug"]: p for p in load_json(json_path, {}).get("contributors", [])}
    overrides = load_overrides()
    gsoc_aliases, gsoc_gitlab = load_gsoc()
    known = waypoint_logins() | set(gsoc_aliases.values())
    idents = collect()

    def people_now():
        resolve(idents, cache, overrides, gsoc_aliases, known)
        return [summarize(g) for g in group(idents)]

    people = people_now()
    if not offline:
        gh = GitHub(GITHUB_BUDGET)
        check_logins(idents, cache)
        people = people_now()
        github_ids(idents, cache, gh)
        github_lookups(people, cache, gh)
        people = people_now()
        check_logins(idents, cache)
        people = people_now()
    forge_index = forge_authors(cache, offline)
    for p in people:
        if p["github"] or p["gitlab"]:
            continue
        for key in [norm(n) for n in p["names"]] + [norm(e.split("@")[0]) for e in p["emails"]]:
            if len(key) >= 5 and len(forge_index.get(key, ())) == 1:
                p["forge"] = next(iter(forge_index[key]))
                break
    on_instance = instance_accounts(people, cache, offline)

    slugs = set()
    for p in people:
        login = p.get("forge") or p["github"] or p["gitlab"]
        if login and login.lower() in on_instance:
            p["source"], p["login"] = "instance", on_instance[login.lower()]
            p["profile"] = f"{INSTANCE}/@{p['login']}"
            base = p["login"].lower()
        elif p["github"]:
            p["source"], p["login"] = "github", p["github"]
            p["profile"] = f"https://github.com/{p['github']}"
            base = p["github"].lower()
        elif p["gitlab"]:
            # gitlab.com/owasp-blt is closed: no gitlab.com profile link or avatar, the name and an identicon.
            p["source"], p["login"], p["profile"] = "git", None, ""
            base = "gitlab-" + p["gitlab"].lower()
        else:
            p["source"], p["login"], p["profile"] = "git", None, ""
            base = "git-" + slugify(p["name"])
        slug, n = slugify(base) if p["source"] == "git" and not base.startswith("gitlab-") \
            else re.sub(r"[^a-z0-9_.-]", "-", base), 2
        while slug in slugs:
            slug, n = f"{base}-{n}", n + 1
        slugs.add(slug)
        p["slug"] = slug
        if p["github"] and not p["gitlab"] and p["github"].lower() in gsoc_gitlab:
            p["gitlab"] = gsoc_gitlab[p["github"].lower()]
    people.sort(key=lambda p: (-p["commits"], p["name"].lower()))

    update_avatars(people, previous, offline)
    for name in os.listdir(OUT_DIR):
        if name.endswith(".png") and name[:-4] not in slugs:
            os.remove(os.path.join(OUT_DIR, name))

    keys = ("slug", "name", "login", "profile", "source", "github", "gitlab", "commits", "first", "last",
            "projects", "avatar", "avatar_kind", "avatar_checked")
    for p in people:
        p["avatar"] = f"{OUT_REL}/{p['slug']}.png"
    doc = {
        "about": "Everyone with a commit in a BLT project (authors and co-authors, bots excluded). "
                 "Generated by scripts/readme/contributors.py.",
        "count": len(people),
        "contributors": [{k: p.get(k) for k in keys} for p in people],
    }
    write_if_changed(json_path, (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode())
    write_if_changed(cache_path, (json.dumps(cache, indent=1, sort_keys=True) + "\n").encode())
    return people


if __name__ == "__main__":
    result = build(offline="--offline" in sys.argv)
    print(json.dumps(Counter(p["source"] for p in result)), len(result))
