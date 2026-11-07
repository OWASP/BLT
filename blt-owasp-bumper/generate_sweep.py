#!/usr/bin/env python3
"""
Write public/data/sweep.json: one row of facts per OWASP project, for the "Suggested projects to
archive" page (public/sweep.html, scored by public/sweep.js). Standard library only, no GitHub
requests of its own; run it after generate_repo_list.py.

    python3 generate_sweep.py

It joins three sources:
  - public/data/repos.json (this project, generate_repo_list.py): every OWASP repository with its
    last commit by a person, archived flag, reminder issues and whether its index.md is still the
    www-project template;
  - the OWASP Project Matrix's repo_status.json (projects.owaspblt.org): the owasp.org inventory's
    projects plus active www-project repositories it doesn't list, each with its code repository's
    GitHub stats (commits and people in 90 days, latest release, stars, top contributors);
  - the Matrix's open_prs.json: every open pull request, to count ones nobody has touched in a year.

Environment: REPOS_FILE (public/data/repos.json), OUTPUT_FILE (public/data/sweep.json),
PROJECTS_URL, OPEN_PRS_URL.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECTS_URL = "https://projects.owaspblt.org/repo_status.json"
OPEN_PRS_URL = "https://projects.owaspblt.org/open_prs.json"
ORG = "owasp"
# Accounts that commit to every project (OWASP staff, bulk edits): not a project's leaders.
NOT_LEADERS = {"owaspfoundation", "owasp-bot", "owaspadmin"}


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "OWASP-Bumper-Sweep"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode())


def reminder(repo: Dict) -> Dict:
    rem = (repo or {}).get("reminder") or {}
    if not rem.get("number"):
        return {}
    last = rem.get("last_reply") or {}
    return {
        "number": rem["number"], "url": rem.get("url", ""), "state": rem.get("state", ""),
        "created": rem.get("created", ""), "closed": rem.get("closed", ""), "replies": rem.get("replies", 0),
        "bumps": rem.get("bumps", 1), "by": rem.get("author", ""), "last_reply_by": last.get("author", ""),
    }


def repo_facts(full: str, bumper: Dict[str, Dict]) -> Dict:
    """What Bumper knows about an OWASP-organization repository ({} for one elsewhere)."""
    owner, _, name = (full or "").partition("/")
    repo = bumper.get(name.lower()) if owner.lower() == ORG else None
    if not repo:
        return {}
    return {
        "human": repo.get("human") or repo.get("pushed", ""),
        "bot_only": bool(repo.get("bot_only")),
        "archived": bool(repo.get("archived")),
        "created": repo.get("created", ""),
        "description": repo.get("description", ""),
        "template_page": bool(repo.get("template_page")),
        "empty": bool(repo.get("empty")),
        "opted_out": bool(repo.get("opted_out")),
        "issues_off": bool(repo.get("issues_off")),
        "reminder": reminder(repo),
    }


def pr_facts(prs: List[Dict], now: datetime) -> Dict[str, Dict]:
    """{lower-case repo: open PRs, ones by people, and ones untouched for a year}."""
    year_ago = (now - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out: Dict[str, Dict] = {}
    for pr in prs:
        f = out.setdefault(pr.get("repo", "").lower(), {"open": 0, "human": 0, "stale": 0, "oldest": ""})
        f["open"] += 1
        if not pr.get("bot"):
            f["human"] += 1
            if pr.get("updated_at", "") < year_ago:
                f["stale"] += 1
        if not f["oldest"] or pr.get("updated_at", "") < f["oldest"]:
            f["oldest"] = pr.get("updated_at", "")
    return out


def project_row(p: Dict, bumper: Dict[str, Dict], prs: Dict[str, Dict]) -> Dict:
    code_full = p.get("repo_name") or ""
    site_full = p.get("www_repo") or ""
    code = {
        "repo": code_full,
        "url": p.get("codeurl") or "",
        "in_org": code_full.lower().startswith(f"{ORG}/"),
        "status": p.get("github_status") or "",
        "archived": bool(p.get("archived")),
        "last_commit": p.get("last_commit") or "",
        "commits_90d": p.get("commits_90d"),
        "people_90d": p.get("contributors_90d"),
        "contributors": p.get("committers"),
        "release": p.get("date_released") or "",
        "stars": p.get("stars"),
        "forks": p.get("forks"),
        "issues": p.get("issues"),
        "prs": prs.get(code_full.lower(), {"open": p.get("prs") or 0, "human": 0, "stale": 0, "oldest": ""}),
        **repo_facts(code_full, bumper),
    }
    site = {"repo": site_full, **repo_facts(site_full, bumper)} if site_full and site_full.lower() != code_full.lower() else {}
    return {
        "slug": p.get("slug") or "",
        "title": p.get("title") or p.get("name") or "",
        "level": str(p.get("level") or "other").lower(),
        "type": p.get("type") or "",
        "listed": p.get("listed") is not False,
        "page": p.get("url") or "",
        "pitch": p.get("pitch") or "",
        "code": code,
        "site": site,
        "leaders": [c["login"] for c in p.get("top_contributors") or []
                    if c.get("login") and c["login"].lower() not in NOT_LEADERS][:3],
    }


def build(projects: List[Dict], repos: List[Dict], prs: List[Dict], now: datetime) -> Dict:
    bumper = {r.get("name", "").lower(): r for r in repos}
    pr_index = pr_facts(prs, now)
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {"projects": PROJECTS_URL, "open_prs": OPEN_PRS_URL, "repos": "data/repos.json"},
        "projects": [project_row(p, bumper, pr_index) for p in projects],
    }


def main():
    repos_file = os.environ.get("REPOS_FILE", os.path.join(HERE, "public", "data", "repos.json"))
    output_file = os.environ.get("OUTPUT_FILE", os.path.join(HERE, "public", "data", "sweep.json"))
    with open(repos_file, encoding="utf-8") as f:
        repos = json.load(f).get("repos", [])
    projects = fetch_json(os.environ.get("PROJECTS_URL", PROJECTS_URL))
    try:
        prs = fetch_json(os.environ.get("OPEN_PRS_URL", OPEN_PRS_URL))
    except Exception as exc:  # the stale-PR signal is a bonus; the sweep works without it
        print(f"Warning: open pull requests unavailable ({exc})", file=sys.stderr)
        prs = []
    if not isinstance(projects, list) or not projects:
        sys.exit("no projects from the Project Matrix; not writing the sweep")
    data = build(projects, repos, prs if isinstance(prs, list) else [], datetime.now(timezone.utc))
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(data['projects'])} projects to {output_file}")


if __name__ == "__main__":
    main()
