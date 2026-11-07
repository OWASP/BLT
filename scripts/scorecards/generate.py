#!/usr/bin/env python3
"""AI scorecards for everyone with an account on git.owaspblt.org.

Every person who opened, reviewed or commented on a BLT issue or pull request on the forge (plus
contributors whose GitHub/GitLab login is also a forge account) gets a small, encouraging scorecard
that the forge shows on their profile page:

  .forkmesh/scorecards/<account name, lower case>.json

What goes in (nothing private, all of it already public on the forge):

  .forkmesh/contributors/contributors.json   commits, projects, first/last commit (scripts/readme)
  .forkmesh/issues/                          issues opened, comments, votes (this checkout)
  forkmesh/pulls ledger branch               pulls opened/merged, reviews, pull comments (git fetch)
  /api/accounts/<name>                       bio, links, followers (profile completeness)

The numbers are scored here, the same way for everyone (score_areas). The AI only writes the words:
a headline, strengths, areas to grow and one next step, and it is told to be warm and specific.
Providers, first one configured wins:

  ANTHROPIC_API_KEY                          Claude (SCORECARD_MODEL, default claude-haiku-5-5)
  CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID   Workers AI (SCORECARD_CF_MODEL)
  neither                                    friendly built-in text from the same numbers

A card is rewritten only when its inputs changed or it is older than REFRESH_DAYS, so a scheduled
run costs a handful of AI calls. Usage:

  python3 scripts/scorecards/generate.py [--force] [--only NAME ...] [--offline] [--dry-run]
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
).stdout.strip()
OUT_DIR = os.path.join(ROOT, ".forkmesh", "scorecards")
CONTRIBUTORS = os.path.join(ROOT, ".forkmesh", "contributors", "contributors.json")
ISSUES_DIR = os.path.join(ROOT, ".forkmesh", "issues")
INSTANCE = os.environ.get("FORKMESH_URL", "https://git.owaspblt.org").rstrip("/")
PULL_LEDGER = "forkmesh/pulls"
PULL_REF = "refs/scorecards/pulls"

SCHEMA = "blt-scorecard-v1"
REFRESH_DAYS = int(os.environ.get("SCORECARD_REFRESH_DAYS", "30"))
CLAUDE_MODEL = os.environ.get("SCORECARD_MODEL", "claude-haiku-5-5")
CF_MODEL = os.environ.get("SCORECARD_CF_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
AI_WORKERS = int(os.environ.get("SCORECARD_AI_WORKERS", "4"))
USER_AGENT = "BLT-Scorecards/1.0"

BOT = re.compile(r"(\[bot\]|-bot$|^bot-|^dependabot|^renovate|^github-actions|^forkbot$|-actions$)", re.I)

# Overall score = weighted mean of the areas. Weights favour the human parts of open source.
AREAS = [
    ("code", "Code", 0.30),
    ("collaboration", "Collaboration", 0.25),
    ("community", "Community", 0.20),
    ("breadth", "Breadth", 0.10),
    ("momentum", "Momentum", 0.15),
]
LEVELS = [(85, "Trailblazer"), (70, "Standout"), (50, "Strong contributor"), (30, "Rising star"),
          (0, "Getting started")]


# ---------------------------------------------------------------- reading


def today():
    return date.today().isoformat()


def ms(value):
    """Seconds or milliseconds -> aware datetime (None for 0/missing)."""
    try:
        value = int(value or 0)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    if value > 10 ** 11:
        value //= 1000
    return datetime.fromtimestamp(value, timezone.utc)


def is_bot(name):
    return not name or bool(BOT.search(name))


def front_matter(text):
    meta, body = {}, text or ""
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end > 0:
            for line in body[3:end].splitlines():
                key, sep, value = line.partition(":")
                if sep:
                    meta[key.strip()] = value.strip()
            body = body[end + 4:]
    return meta, body


def read_issues():
    found = []
    for dirpath, _, files in os.walk(ISSUES_DIR):
        for name in files:
            if name.startswith("issue-") and name.endswith(".json"):
                try:
                    with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                        found.append(json.load(fh))
                except (OSError, ValueError):
                    continue
    return found


def read_pulls(offline):
    """[(front matter, [event front matter])] from the pull ledger branch (fetched into PULL_REF)."""
    if not offline:
        subprocess.run(["git", "fetch", "-q", f"{INSTANCE}/BLT.git", f"+{PULL_LEDGER}:{PULL_REF}"],
                       cwd=ROOT, capture_output=True, timeout=300)
    listing = subprocess.run(["git", "ls-tree", "-r", PULL_REF, ".forkmesh/pulls/"], cwd=ROOT,
                             capture_output=True, text=True)
    if listing.returncode != 0:
        print("scorecards: no pull ledger available, pulls skipped", file=sys.stderr)
        return []
    paths = [line.split("\t", 1)[1] for line in listing.stdout.splitlines() if "\t" in line]
    paths = [p for p in paths if p.endswith(".md")]
    texts = cat_files(paths)
    pulls = defaultdict(lambda: [None, []])
    for path in paths:
        parts = path.split("/")
        if len(parts) != 4:
            continue
        meta, _ = front_matter(texts.get(path, ""))
        if parts[3] == "pull.md":
            pulls[parts[2]][0] = meta
        else:
            pulls[parts[2]][1].append(meta)
    return [(head, events) for head, events in pulls.values()
            if head and head.get("status", "").lower() != "deleted"]


def cat_files(paths):
    if not paths:
        return {}
    spec = "".join(f"{PULL_REF}:{p}\n" for p in paths).encode()
    out = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT, input=spec, capture_output=True).stdout
    texts, pos = {}, 0
    for path in paths:
        nl = out.index(b"\n", pos)
        header = out[pos:nl].split()
        pos = nl + 1
        if len(header) < 3 or header[1] == b"missing":
            continue
        size = int(header[2])
        texts[path] = out[pos:pos + size].decode("utf-8", "replace")
        pos += size + 1
    return texts


def http_json(url, data=None, headers=None, timeout=30):
    body = json.dumps(data).encode() if data is not None else None
    request = Request(url, data=body, headers={"User-Agent": USER_AGENT, "Accept": "application/json",
                                               **({"Content-Type": "application/json"} if body else {}),
                                               **(headers or {})})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (429, 500, 502, 503, 504, 529) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except URLError:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    return None


def account(name):
    try:
        data = http_json(f"{INSTANCE}/api/accounts/{name.lower()}", timeout=15)
    except (HTTPError, URLError, ValueError, OSError):
        return name, None
    if not data or not data.get("exists") or data.get("kind") not in (None, "", "user"):
        return name, None
    if data.get("profilePrivate") or str(data.get("status") or "active") != "active":
        return name, None
    return name, data


# ---------------------------------------------------------------- facts


def blank():
    return {"commits": 0, "projects": [], "first_commit": None, "last_commit": None,
            "pulls_opened": 0, "pulls_merged": 0, "pulls_open": 0, "reviews_given": 0,
            "approvals_given": 0, "pull_comments": 0, "issues_opened": 0, "issue_comments": 0,
            "votes_cast": 0, "issue_projects": set(), "pull_projects": set(), "last_active": None}


def touch(facts, when):
    if when and (facts["last_active"] is None or when > facts["last_active"]):
        facts["last_active"] = when


def project_of(title):
    match = re.match(r"\s*\[?((?:blt-|my-gsoc-tool|coderabbit)[a-z0-9-]*)\]?\s*[:\]]", title or "", re.I)
    return match.group(1).lower() if match else None


def gather(offline):
    people = defaultdict(blank)
    for issue in read_issues():
        author = issue.get("authorName") or ""
        if not is_bot(author):
            f = people[author.lower()]
            f["issues_opened"] += 1
            touch(f, ms(issue.get("createdAt")))
            if project_of(issue.get("title")):
                f["issue_projects"].add(project_of(issue.get("title")))
        for event in issue.get("events") or []:
            name = (event or {}).get("authorName") or ""
            if is_bot(name):
                continue
            kind = event.get("type")
            if kind == "comment":
                people[name.lower()]["issue_comments"] += 1
            elif kind == "vote":
                people[name.lower()]["votes_cast"] += 1
            else:
                continue
            touch(people[name.lower()], ms(event.get("ts")))

    for head, events in read_pulls(offline):
        author = head.get("authorName") or ""
        if not is_bot(author):
            f = people[author.lower()]
            f["pulls_opened"] += 1
            status = head.get("status", "").lower()
            f["pulls_merged"] += status == "merged"
            f["pulls_open"] += status == "open"
            touch(f, ms(head.get("mergedAt")) or ms(head.get("ts")))
            if project_of(head.get("title")):
                f["pull_projects"].add(project_of(head.get("title")))
        for event in events:
            name = event.get("authorName") or ""
            if is_bot(name) or name.lower() == author.lower() and event.get("type") == "review":
                continue
            if event.get("type") == "review":
                people[name.lower()]["reviews_given"] += 1
                people[name.lower()]["approvals_given"] += event.get("state") == "approved"
            elif event.get("type") == "comment":
                people[name.lower()]["pull_comments"] += 1
            else:
                continue
            touch(people[name.lower()], ms(event.get("ts")))

    try:
        with open(CONTRIBUTORS, encoding="utf-8") as fh:
            contributors = json.load(fh).get("contributors") or []
    except (OSError, ValueError):
        contributors = []
    by_login = {}
    for c in contributors:
        for login in {c.get("login"), c.get("github"), c.get("gitlab")}:
            if login:
                by_login.setdefault(login.lower(), c)

    # Contributors with commits but no forge activity yet still get a card if they have an account.
    candidates = set(people) | set(by_login)
    accounts = {}
    if not offline:
        with ThreadPoolExecutor(8) as pool:
            for name, data in pool.map(account, sorted(n for n in candidates if not is_bot(n))):
                if data:
                    accounts[name] = data

    result = {}
    for name, data in accounts.items():
        f = people[name]
        c = by_login.get(name)
        if c:
            f["commits"] = int(c.get("commits") or 0)
            f["projects"] = [p.lower() for p in c.get("projects") or []]
            f["first_commit"] = c.get("first")
            f["last_commit"] = c.get("last")
            if c.get("last"):
                touch(f, datetime.fromisoformat(c["last"]).replace(tzinfo=timezone.utc))
        f["profile"] = {
            "bio": bool((data.get("profileBio") or data.get("profileAbout") or "").strip()),
            "readme": bool((data.get("profileReadme") or "").strip()),
            "links": len(data.get("profileLinks") or []),
            "location": bool((data.get("profileLocation") or "").strip()),
            "followers": int(data.get("followers") or 0),
            "joined": ms(data.get("createdAt")).date().isoformat() if ms(data.get("createdAt")) else None,
        }
        if sum((f["commits"], f["pulls_opened"], f["reviews_given"], f["issues_opened"],
                f["issue_comments"], f["pull_comments"], f["votes_cast"])) == 0 and not any(f["profile"].values()):
            continue  # an empty account: nothing to say yet
        result[data.get("nameCase") or data.get("name") or name] = f
    return result


# ---------------------------------------------------------------- scoring


def curve(value, full):
    """0..100, logarithmic: `full` reaches 100, the first few count the most."""
    if value <= 0:
        return 0
    return min(100, round(100 * math.log1p(value) / math.log1p(full)))


def score_areas(f, now=None):
    now = now or datetime.now(timezone.utc)
    projects = set(f["projects"]) | f["issue_projects"] | f["pull_projects"]
    p = f.get("profile") or {}
    days = (now - f["last_active"]).days if f["last_active"] else None
    if days is None:
        momentum = 10
    elif days <= 14:
        momentum = 100
    else:
        momentum = max(20, round(100 - (days - 14) * 0.45))
    areas = {
        "code": round(0.6 * curve(f["commits"], 400) + 0.4 * curve(f["pulls_merged"], 25)),
        "collaboration": round(0.6 * curve(f["reviews_given"], 30)
                               + 0.4 * curve(f["pull_comments"] + f["issue_comments"], 80)),
        "community": round(0.5 * curve(f["issues_opened"], 20) + 0.2 * curve(f["votes_cast"], 20)
                           + 0.3 * min(100, 30 * p.get("bio", 0) + 25 * p.get("readme", 0)
                                       + 15 * min(p.get("links", 0), 2) + 15 * p.get("location", 0))),
        "breadth": curve(len(projects), 12),
        "momentum": momentum,
    }
    overall = sum(areas[key] * weight for key, _, weight in AREAS)
    # Encouraging by design: anyone who showed up starts from 20.
    overall = max(20, round(overall))
    level = next(label for floor, label in LEVELS if overall >= floor)
    return overall, level, areas, sorted(projects)


# ---------------------------------------------------------------- writing


SYSTEM = (
    "You write tiny scorecards for contributors to OWASP BLT, an open-source security community. "
    "Write to the contributor as \"you\", like a kind, upbeat mentor. Celebrate real work using the "
    "actual numbers and project names given, and frame areas to improve as exciting next opportunities, "
    "never as failures or low scores. Never mention scores, areas or ratings by name; talk about the work. "
    "Never invent facts, projects or numbers that are not in the data. No emojis. Plain text only. "
    "Answer with JSON only: {\"headline\": str (one warm sentence, max 90 chars), "
    "\"strengths\": [2-3 str, each a specific achievement with a number or project, max 70 chars], "
    "\"grow\": [2-3 str, each a friendly concrete suggestion, max 90 chars], "
    "\"next_step\": str (max 110 chars, one concrete thing to try next on git.owaspblt.org)}\n"
    "Example: {\"headline\": \"You turned 3 pull requests into real fixes for blt-leaf this month.\", "
    "\"strengths\": [\"1 merged pull request in blt-leaf\", \"5 thoughtful comments on pull requests\"], "
    "\"grow\": [\"Reviewing a teammate's pull request is a great way to learn new corners of BLT\", "
    "\"A short bio on your profile helps others find you for help\"], "
    "\"next_step\": \"Pick an open issue in blt-leaf and leave a review on one pull request this week\"}"
)


def prompt_for(name, f, overall, level, areas, projects):
    p = f.get("profile") or {}
    lines = [
        f"Contributor: {name}",
        f"Overall score: {overall}/100 ({level})",
        "Area scores (0-100): " + ", ".join(f"{label} {areas[key]}" for key, label, _ in AREAS),
        f"Commits in BLT history: {f['commits']}"
        + (f" (first {f['first_commit']}, latest {f['last_commit']})" if f["first_commit"] else ""),
        f"Pull requests on the forge: {f['pulls_opened']} opened, {f['pulls_merged']} merged, {f['pulls_open']} still open",
        f"Reviews given on others' pull requests: {f['reviews_given']} ({f['approvals_given']} approvals)",
        f"Comments: {f['pull_comments']} on pull requests, {f['issue_comments']} on issues",
        f"Issues opened: {f['issues_opened']}; issue votes cast: {f['votes_cast']}",
        f"Projects touched: {', '.join(projects) if projects else 'none yet'}",
        f"Profile: bio {'yes' if p.get('bio') else 'no'}, readme {'yes' if p.get('readme') else 'no'}, "
        f"{p.get('links', 0)} links, {p.get('followers', 0)} followers, joined {p.get('joined') or 'unknown'}",
        f"Last activity: {f['last_active'].date().isoformat() if f['last_active'] else 'unknown'} (today is {today()})",
    ]
    return "\n".join(lines)


def ask_claude(prompt):
    data = http_json("https://api.anthropic.com/v1/messages", {
        "model": CLAUDE_MODEL, "max_tokens": 600, "system": SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }, headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"}, timeout=60)
    return "".join(part.get("text", "") for part in (data or {}).get("content") or []), CLAUDE_MODEL


def ask_workers_ai(prompt):
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    data = http_json(f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{CF_MODEL}", {
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "max_tokens": 600, "temperature": 0.6,
    }, headers={"Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}"}, timeout=60)
    result = (data or {}).get("result") or {}
    text = result.get("response")
    if text is None and result.get("choices"):
        text = result["choices"][0].get("message", {}).get("content")
    if isinstance(text, (dict, list)):
        text = json.dumps(text)
    return text or "", CF_MODEL.rsplit("/", 1)[-1]


def provider():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return ask_claude
    if os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        return ask_workers_ai
    return None


def clip(text, limit):
    text = re.sub(r"\s+", " ", str(text or "")).strip().strip('"')
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:-")
    return cut + "…"


def parse_words(text):
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    strengths = [clip(s, 80) for s in data.get("strengths") or [] if str(s).strip()][:3]
    grow = [clip(s, 100) for s in data.get("grow") or [] if str(s).strip()][:3]
    if not data.get("headline") or not strengths or not grow:
        return None
    return {"headline": clip(data["headline"], 100), "strengths": strengths, "grow": grow,
            "next_step": clip(data.get("next_step") or "", 120)}


def builtin_words(name, f, areas, projects):
    """Friendly text from the numbers alone, when no AI is configured or it answered badly."""
    strengths, grow = [], []
    if f["commits"]:
        strengths.append(f"{f['commits']} commits across BLT's history")
    if f["pulls_merged"]:
        strengths.append(f"{f['pulls_merged']} merged pull request{'s' * (f['pulls_merged'] != 1)} on the forge")
    if f["reviews_given"]:
        strengths.append(f"{f['reviews_given']} review{'s' * (f['reviews_given'] != 1)} that helped others ship")
    if f["issues_opened"]:
        strengths.append(f"{f['issues_opened']} issue{'s' * (f['issues_opened'] != 1)} opened to improve BLT")
    if len(projects) > 1:
        strengths.append(f"Work spread over {len(projects)} projects")
    if not strengths:
        strengths.append("Joined the BLT community on the forge")
    ranked = sorted(areas, key=lambda key: areas[key])
    tips = {
        "code": "Pick a good-first-issue and open a pull request; small fixes count",
        "collaboration": "Reviewing a teammate's pull request is a great way to learn the codebase",
        "community": "Open an issue for a bug or idea you spotted, or add a bio to your profile",
        "breadth": "Explore another BLT project; there are dozens to discover",
        "momentum": "A small contribution this month would get your streak going again",
    }
    grow = [tips[key] for key in ranked[:2]]
    level_area = ranked[0]
    return {
        "headline": f"Thanks for building BLT with us, {name}!",
        "strengths": strengths[:3],
        "grow": grow,
        "next_step": {
            "code": "Browse open issues on git.owaspblt.org/BLT/issues and claim one that sparks your interest",
            "collaboration": "Leave a friendly review on an open pull request this week",
            "community": "Share an idea or bug as a new issue on git.owaspblt.org/BLT",
            "breadth": "Read the README of a BLT project you have not tried yet",
            "momentum": "Come back for a quick fix or review this week; every bit helps",
        }[level_area],
    }


def facts_json(f):
    out = {k: v for k, v in f.items() if k not in ("issue_projects", "pull_projects", "last_active", "profile")}
    out["last_active"] = f["last_active"].date().isoformat() if f["last_active"] else None
    out["profile"] = f.get("profile") or {}
    return out


def card_for(name, f, ask, force):
    path = os.path.join(OUT_DIR, f"{name.lower()}.json")
    overall, level, areas, projects = score_areas(f)
    stats = facts_json(f)
    stats.pop("projects", None)
    digest = hashlib.sha256(json.dumps([overall, areas, stats, projects], sort_keys=True,
                                       default=str).encode()).hexdigest()[:16]
    try:
        with open(path, encoding="utf-8") as fh:
            old = json.load(fh)
    except (OSError, ValueError):
        old = {}
    try:
        age = (date.today() - date.fromisoformat(old.get("generated") or "")).days
    except ValueError:
        age = REFRESH_DAYS
    # Keep an unchanged, recent card, unless it holds built-in text and an AI is now available.
    upgrade = ask is not None and old.get("model") == "builtin"
    if not force and not upgrade and old.get("inputs") == digest and age < REFRESH_DAYS:
        return path, None
    words, model = None, "builtin"
    if ask:
        prompt = prompt_for(name, f, overall, level, areas, projects)
        for _ in range(2):
            try:
                text, used = ask(prompt)
            except (HTTPError, URLError, OSError, ValueError, KeyError) as exc:
                print(f"scorecards: {name}: AI call failed ({exc})", file=sys.stderr)
                break
            words = parse_words(text)
            if words:
                model = used
                break
    words = words or builtin_words(name, f, areas, projects)
    card = {
        "schema": SCHEMA,
        "login": name,
        "generated": today(),
        "model": model,
        "inputs": digest,
        "score": overall,
        "level": level,
        "areas": [{"key": key, "label": label, "score": areas[key]} for key, label, _ in AREAS],
        **words,
        "stats": {
            "commits": f["commits"], "pulls_merged": f["pulls_merged"], "reviews": f["reviews_given"],
            "issues": f["issues_opened"], "comments": f["issue_comments"] + f["pull_comments"],
            "projects": len(projects), "last_active": stats["last_active"],
        },
        "about": "Generated by scripts/scorecards/generate.py from public BLT activity. "
                 "Areas are scored the same way for everyone; the words are AI-written.",
    }
    return path, card


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--force", action="store_true", help="rewrite every card, even unchanged ones")
    parser.add_argument("--only", nargs="*", default=[], help="account names to (re)write")
    parser.add_argument("--offline", action="store_true", help="no network: skip accounts and the AI")
    parser.add_argument("--dry-run", action="store_true", help="print cards instead of writing them")
    parser.add_argument("--limit", type=int, default=0, help="write at most this many cards")
    args = parser.parse_args(argv)

    people = gather(args.offline)
    only = {n.lower() for n in args.only}
    if only:
        people = {n: f for n, f in people.items() if n.lower() in only}
    ask = None if args.offline else provider()
    print(f"scorecards: {len(people)} people, writer: {ask.__name__ if ask else 'builtin'}", file=sys.stderr)
    os.makedirs(OUT_DIR, exist_ok=True)

    names = sorted(people, key=str.lower)
    if args.limit:
        names = names[:args.limit]
    written = 0
    with ThreadPoolExecutor(max(1, AI_WORKERS)) as pool:
        for path, card in pool.map(lambda n: card_for(n, people[n], ask, args.force or bool(only)), names):
            if card is None:
                continue
            written += 1
            text = json.dumps(card, indent=1, ensure_ascii=False) + "\n"
            if args.dry_run:
                print(text)
            else:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
    # Accounts that are gone (deleted, private, renamed) lose their card.
    keep = {n.lower() for n in people}
    if not only and not args.dry_run and not args.limit and not args.offline:
        for name in os.listdir(OUT_DIR):
            if name.endswith(".json") and name[:-5] not in keep:
                os.remove(os.path.join(OUT_DIR, name))
    print(f"scorecards: {written} written", file=sys.stderr)


if __name__ == "__main__":
    main()
