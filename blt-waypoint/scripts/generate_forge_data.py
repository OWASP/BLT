#!/usr/bin/env python3
"""Per-folder project data from git.owaspblt.org into public/forge_data.json.

Replaces the gitlab.com/owasp-blt reader. One repository row per project folder of the monorepo
(scripts/routing/projects.tsv):

- commits: ``history?path=<folder>`` (scripts/forkmesh/ledger.py), paged back to 365 days or
  FORGE_HISTORY_PAGES pages; counts for 30/90/365 days, last commit, distinct authors, 26 weekly
  counts. ``commits_truncated`` marks a folder whose page cap was reached before 365 days.
- issues and pull requests: the forge ledgers, attributed to folders by label (``<folder>`` or
  ``project:<folder>``), else by title prefix (``[<folder>]`` / ``<folder>:``).
- description, website, topics: ``<folder>/.forkmesh/info.json`` where present (read from the
  checkout), else the description in data/github_archive.json (the archived GitHub record).
- README size and wrangler.toml presence: from the checkout.
- rating: gold, silver or bronze against the checklist in scripts/ratings.py, and gold_issue, the
  folder's open issue labelled ``gold-standard``.
- live_url: the custom domain of the folder's Worker (scripts/live_sites.py; Cloudflare's domain
  list when CLOUDFLARE_API_TOKEN is set, else the wrangler.toml routes), else the info.json website.

Stars, forks, languages, releases, tags, branches and repository size do not exist per folder:
those fields are null. FORGE_BUDGET_SECONDS (default 300) bounds the run; when it runs out the
script exits non-zero without writing, so the previous data keeps being served.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import forge_urls  # noqa: E402
import live_sites  # noqa: E402
import ratings  # noqa: E402

ROOT = forge_urls.ROOT
sys.path.insert(0, os.path.join(ROOT, "scripts", "forkmesh"))
import ledger  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.getenv("FORGE_DATA_OUT", os.path.join(PROJECT, "public", "forge_data.json"))
GITHUB_DATA = os.path.join(PROJECT, "data", "github_archive.json")
BUDGET = float(os.getenv("FORGE_BUDGET_SECONDS", "300"))
MAX_PAGES = int(os.getenv("FORGE_HISTORY_PAGES", "20"))
WINDOWS = (30, 90, 365)
WEEKS = 26
BOT = re.compile(r"(\[bot\]$|-actions$|^github-actions|^dependabot|^renovate)", re.I)


def is_bot(name):
    return bool(BOT.search(str(name or "")))


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def folder_info(root, folder):
    """{description, website, topics} from <folder>/.forkmesh/info.json, or {}."""
    text = read_text(os.path.join(root, folder, ".forkmesh", "info.json"))
    try:
        info = json.loads(text) if text else {}
    except ValueError:
        info = {}
    if not isinstance(info, dict):
        return {}
    topics = info.get("topics") or []
    if isinstance(topics, str):
        topics = [t.strip() for t in topics.split(",")]
    return {
        "description": info.get("about") or info.get("description") or None,
        "website": info.get("website") or info.get("homepage") or None,
        "topics": [str(t) for t in topics if str(t).strip()],
    }


def readme_chars(root, folder):
    for name in ("README.md", "readme.md", "README"):
        text = read_text(os.path.join(root, folder, name))
        if text is not None:
            return len(text)
    return 0


def github_descriptions(index):
    """Folder -> description from the archived GitHub record (fallback only)."""
    try:
        with open(GITHUB_DATA, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    found = {}
    for repo in data.get("repos") or []:
        folder = forge_urls.resolve(repo.get("name"), index)
        if folder and repo.get("description") and folder not in found:
            found[folder] = repo["description"]
    return found


def commit_stats(commits, now, truncated=False):
    """Counts, authors and the weekly series of a folder's commits (newest first)."""
    stats = {f"commits_{d}d": 0 for d in WINDOWS}
    weekly = [0] * WEEKS
    authors = {}
    for commit in commits:
        when = ledger.iso_to_dt(commit.get("date"))
        name = commit.get("author") or ""
        if not when or is_bot(name):
            continue
        age = now - when
        for days in WINDOWS:
            if age <= timedelta(days=days):
                stats[f"commits_{days}d"] += 1
        week = age.days // 7
        if 0 <= week < WEEKS:
            weekly[WEEKS - 1 - week] += 1
        if name and age <= timedelta(days=365):
            authors[name] = authors.get(name, 0) + 1
    latest = commits[0] if commits else None
    latest_at = iso(ledger.iso_to_dt(latest.get("date"))) if latest else None
    stats.update({
        "commits_truncated": bool(truncated),
        "last_commit_at": latest_at,
        "weekly_commits": weekly,
        "contributor_count": len(authors),
        "contributors": [
            {"login": name, "avatar_url": "", "html_url": "", "contributions": count}
            for name, count in sorted(authors.items(), key=lambda item: (-item[1], item[0].lower()))[:10]
        ],
        "latest_commit": {
            "sha": (latest.get("hash") or "")[:7],
            "message": (latest.get("subject") or "").split("\n")[0],
            "author": latest.get("author"),
            "author_avatar": "",
            "author_html_url": "",
            "html_url": f"{forge_urls.WEB_URL}/commit/{latest.get('hash')}",
            "date": latest_at,
        } if latest else None,
    })
    return stats


def user(name):
    return {"login": name or "unknown", "avatar_url": "", "html_url": ledger.profile_url(name)}


def issue_entry(issue, folder, name):
    labels = [l.get("name") if isinstance(l, dict) else l for l in issue.get("labels") or []]
    assignees = []
    for a in issue.get("assignees") or []:
        login = a.get("name") or a.get("login") if isinstance(a, dict) else a
        if login:
            assignees.append(user(str(login)))
    return {
        "number": issue.get("number"),
        "title": issue.get("title") or "",
        "html_url": ledger.issue_url(issue.get("number")),
        "created_at": ledger.ms_to_iso(issue.get("createdAt")),
        "updated_at": ledger.ms_to_iso(issue.get("updatedAt")) or ledger.ms_to_iso(issue.get("createdAt")),
        "user": user(issue.get("authorName")),
        "labels": [{"name": str(l), "color": ""} for l in labels if l],
        "assignees": assignees,
        "linked_prs": [],
        "votes": ledger.vote_count(issue),
        "comments": len(ledger.comments(issue)),
        "folder": folder,
        "repo_name": name,
        "repo_html_url": forge_urls.folder_url(folder) if folder else forge_urls.WEB_URL,
    }


def pull_projects(pull, folders):
    names = []
    for label in ledger.fs.label_projects(pull.get("labels") if isinstance(pull.get("labels"), list) else []):
        if label in folders:
            names.append(label)
    prefix = ledger.title_project(pull.get("title"))
    if not names and prefix in folders:
        names.append(prefix)
    return names


def pull_entry(pull):
    status = str(pull.get("status") or "open").lower()
    state = "merged" if status in ("merged", "closed-merged") else ("open" if status == "open" else "closed")
    name = pull.get("authorName")
    return {
        "number": pull.get("number"),
        "title": pull.get("title") or "",
        "html_url": f"{forge_urls.WEB_URL}/pulls/{pull.get('number')}",
        "state": state,
        "author": name,
        "author_avatar": "",
        "author_html_url": ledger.profile_url(name),
        "updated_at": ledger.ms_to_iso(pull.get("updatedAt")) or ledger.ms_to_iso(pull.get("ts")),
    }


def old_folders(root, folder, aliases):
    """Aliases that name a former folder of this project: lower-case blt-* names with no folder now."""
    return [a for a in aliases if a != folder and a == a.lower() and a.startswith("blt-")
            and not os.path.isdir(os.path.join(root, a))]


def build(client, root=ROOT, now=None, max_pages=MAX_PAGES, domains=None):
    """The forge_data.json payload. Raises ledger.DeadlineExceeded when the budget runs out."""
    now = now or datetime.now(timezone.utc)
    index = forge_urls.folder_index(root)
    projects = forge_urls.projects(root)
    folders = {folder for folder, _, _ in projects}
    names = {folder: name for folder, name, _ in projects}
    fallback = github_descriptions(index)
    sites = live_sites.live_urls(root, sorted(folders), domains)

    open_issues, issues_by_folder = [], {}
    for issue in ledger.issues(client):
        if not ledger.is_open(issue):
            continue
        attributed = [f for f in ledger.issue_projects(issue) if f in folders]
        folder = attributed[0] if attributed else None
        entry = issue_entry(issue, folder, names.get(folder, "BLT"))
        open_issues.append(entry)
        for f in attributed:
            issues_by_folder.setdefault(f, []).append(entry)

    pulls_by_folder = {}
    for pull in ledger.pulls(client):
        for f in pull_projects(pull, folders):
            pulls_by_folder.setdefault(f, []).append(pull)

    since = now - timedelta(days=max(WINDOWS))
    repos = []
    for folder, name, aliases in projects:
        commits = ledger.history(client, folder, since=since, max_pages=max_pages)
        truncated = len(commits) >= max_pages * ledger.HISTORY_PAGE
        # A renamed or merged folder keeps its old folder names as aliases (blt-timer-web ->
        # blt-timer); path history doesn't follow renames, so add theirs.
        seen = {c.get("hash") for c in commits}
        olds = old_folders(root, folder, aliases)
        for old in olds:
            for c in ledger.history(client, old, since=since, max_pages=max_pages):
                if c.get("hash") not in seen:
                    seen.add(c.get("hash"))
                    commits.append(c)
        if olds:
            commits.sort(key=lambda c: ledger.iso_to_dt(c.get("date")) or datetime.min.replace(tzinfo=timezone.utc),
                         reverse=True)
        info = folder_info(root, folder)
        stats = commit_stats(commits, now, truncated)
        folder_issues = sorted(issues_by_folder.get(folder, []), key=lambda i: i["updated_at"] or "", reverse=True)
        folder_pulls = sorted(pulls_by_folder.get(folder, []),
                              key=lambda p: int(p.get("updatedAt") or p.get("ts") or 0), reverse=True)
        open_pulls = [p for p in folder_pulls if str(p.get("status") or "open").lower() == "open"]
        repos.append({
            "id": folder,
            "name": name,
            "folder": folder,
            "full_name": f"BLT/{folder}",
            "html_url": forge_urls.folder_url(folder),
            "issues_url": f"{forge_urls.WEB_URL}/issues?label={folder}",
            "description": info.get("description") or fallback.get(folder),
            "homepage": info.get("website"),
            "live_url": sites.get(folder) or info.get("website"),
            "topics": info.get("topics") or [],
            "private": False,
            "fork": False,
            "archived": False,
            "default_branch": "main",
            "created_at": None,
            "updated_at": stats["last_commit_at"],
            "pushed_at": stats["last_commit_at"],
            "open_issues_count": len(folder_issues),
            "open_pr_count": len(open_pulls),
            "readme_chars": readme_chars(root, folder),
            "has_wrangler_toml": os.path.isfile(os.path.join(root, folder, "wrangler.toml")),
            "has_pages": False,
            "latest_issue": folder_issues[0] if folder_issues else None,
            "latest_pr": pull_entry(folder_pulls[0]) if folder_pulls else None,
            # Not available per folder on the forge.
            "language": None,
            "stargazers_count": None,
            "forks_count": None,
            "size": None,
            "branch_count": None,
            "agent_pr_count": None,
            "total_commits": None,
            "latest_release": None,
            "license": None,
            "star_history": [],
            **stats,
        })

    return ratings.apply({
        "generated_at": iso(now),
        "source": "forge",
        "org": "BLT",
        "forge_url": forge_urls.WEB_URL,
        "unavailable": ["language", "stargazers_count", "forks_count", "size", "branch_count",
                        "agent_pr_count", "total_commits", "latest_release"],
        "cumulative": {
            "total_repos": len(repos),
            "active_repos": sum(1 for r in repos if r["commits_90d"]),
            "total_open_issues": len(open_issues),
            "total_open_prs": sum(r["open_pr_count"] for r in repos),
            **{f"commits_{d}d": sum(r[f"commits_{d}d"] for r in repos) for d in WINDOWS},
            "total_readme_chars": sum(r["readme_chars"] for r in repos),
            "total_topics": len({t for r in repos for t in r["topics"]}),
        },
        "repos": repos,
        "open_issues": sorted(open_issues, key=lambda i: i["updated_at"] or "", reverse=True),
    }, root, now)


def main():
    client = ledger.client(seconds=BUDGET)
    try:
        payload = build(client, domains=live_sites.cloudflare_domains())
    except ledger.DeadlineExceeded:
        print(f"forge data: time budget of {BUDGET:.0f}s spent after {client.requests} request(s); "
              f"keeping the previous data", file=sys.stderr)
        return 1
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"), ensure_ascii=False)
        handle.write("\n")
    print(f"forge data: {len(payload['repos'])} folders, {len(payload['open_issues'])} open issues, "
          f"{client.requests} request(s) -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
