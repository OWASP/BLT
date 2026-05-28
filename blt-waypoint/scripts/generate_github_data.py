#!/usr/bin/env python3
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
ORG = os.getenv("GITHUB_ORG", "OWASP-BLT")
OUT = os.getenv("GITHUB_DATA_OUT", "github_data.json")
TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "blt-waypoint-data-generator",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8")), resp.headers


def all_pages(url):
    items = []
    page = 1
    joiner = "&" if "?" in url else "?"
    while True:
        data, _headers = request_json(f"{url}{joiner}per_page=100&page={page}")
        if not data:
            break
        items.extend(data)
        if len(data) < 100:
            break
        page += 1
    return items


def count_items(url):
    try:
        data, headers = request_json(f"{url}{'&' if '?' in url else '?'}per_page=1")
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404, 409):
            return 0
        raise
    link = headers.get("Link", "")
    if 'rel="last"' in link:
        for part in link.split(","):
            if 'rel="last"' in part:
                parsed = urllib.parse.urlparse(part[part.find("<") + 1:part.find(">")])
                qs = urllib.parse.parse_qs(parsed.query)
                return int(qs.get("page", ["1"])[0])
    return len(data) if isinstance(data, list) else 0


def optional_json(url, default=None):
    try:
        data, _headers = request_json(url)
        return data
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404, 409):
            return default
        raise


def readme_chars(repo):
    data = optional_json(f"{API}/repos/{ORG}/{repo}/readme", {})
    if not data or not data.get("content"):
        return 0
    try:
        return len(base64.b64decode(data["content"]).decode("utf-8", "ignore"))
    except Exception:
        return 0


def latest_pr(repo):
    prs = optional_json(
        f"{API}/repos/{ORG}/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=1",
        [],
    )
    if not prs:
        return None
    pr = prs[0]
    state = "merged" if pr.get("merged_at") else pr.get("state")
    return {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "html_url": pr.get("html_url"),
        "state": state,
        "author": (pr.get("user") or {}).get("login"),
        "author_avatar": (pr.get("user") or {}).get("avatar_url"),
        "author_html_url": (pr.get("user") or {}).get("html_url"),
        "updated_at": pr.get("updated_at"),
    }


def latest_issue(repo):
    issues = optional_json(
        f"{API}/repos/{ORG}/{repo}/issues?state=open&sort=updated&direction=desc&per_page=10",
        [],
    )
    for issue in issues or []:
        if "pull_request" in issue:
            continue
        return {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "html_url": issue.get("html_url"),
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
            "user": issue.get("user"),
            "labels": issue.get("labels", []),
            "assignees": issue.get("assignees", []),
            "linked_prs": [],
            "repo_name": repo,
            "repo_html_url": f"https://github.com/{ORG}/{repo}",
        }
    return None


def normalize_repo(r):
    name = r["name"]
    contributors = optional_json(f"{API}/repos/{ORG}/{name}/contributors?per_page=10", []) or []
    branches = count_items(f"{API}/repos/{ORG}/{name}/branches")
    commits = count_items(f"{API}/repos/{ORG}/{name}/commits")
    latest_commit_data = optional_json(f"{API}/repos/{ORG}/{name}/commits?per_page=1", []) or []
    releases = optional_json(f"{API}/repos/{ORG}/{name}/releases?per_page=1", []) or []
    pulls_open = optional_json(f"{API}/repos/{ORG}/{name}/pulls?state=open&per_page=100", []) or []
    issues_count = max(0, (r.get("open_issues_count") or 0) - len(pulls_open))
    latest_commit = None
    if latest_commit_data:
        c = latest_commit_data[0]
        author = c.get("author") or {}
        commit = c.get("commit") or {}
        latest_commit = {
            "sha": (c.get("sha") or "")[:7],
            "message": (commit.get("message") or "").split("\n")[0],
            "author": (commit.get("author") or {}).get("name"),
            "author_avatar": author.get("avatar_url"),
            "author_html_url": author.get("html_url"),
            "html_url": c.get("html_url"),
            "date": (commit.get("author") or {}).get("date"),
        }
    return {
        **r,
        "open_issues_count": issues_count,
        "readme_chars": readme_chars(name),
        "contributors": contributors,
        "total_commits": commits,
        "weekly_commits": [],
        "file_count": 0,
        "branch_count": branches,
        "open_pr_count": len(pulls_open),
        "agent_pr_count": sum(1 for pr in pulls_open if ((pr.get("user") or {}).get("login") or "").lower().startswith("copilot")),
        "latest_issue": latest_issue(name),
        "latest_commit": latest_commit,
        "latest_pr": latest_pr(name),
        "latest_release": releases[0] if releases else None,
        "star_history": [],
        "has_wrangler_toml": optional_json(f"{API}/repos/{ORG}/{name}/contents/wrangler.toml", None) is not None,
    }


def main():
    repos = [normalize_repo(r) for r in all_pages(f"{API}/orgs/{ORG}/repos?sort=updated&type=all")]
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "github",
        "org": ORG,
        "cumulative": {
            "total_repos": len(repos),
            "active_repos": sum(1 for r in repos if not r.get("archived")),
            "total_stars": sum(r.get("stargazers_count") or 0 for r in repos),
            "total_forks": sum(r.get("forks_count") or 0 for r in repos),
            "total_open_issues": sum(r.get("open_issues_count") or 0 for r in repos),
            "total_open_prs": sum(r.get("open_pr_count") or 0 for r in repos),
            "total_agent_prs": sum(r.get("agent_pr_count") or 0 for r in repos),
            "total_size_kb": sum(r.get("size") or 0 for r in repos),
            "total_topics": len({t for r in repos for t in r.get("topics", [])}),
            "total_languages": len({r.get("language") for r in repos if r.get("language")}),
            "total_readme_chars": sum(r.get("readme_chars") or 0 for r in repos),
            "total_branches": sum(r.get("branch_count") or 0 for r in repos),
        },
        "repos": repos,
        "open_issues": [r["latest_issue"] for r in repos if r.get("latest_issue")],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
        f.write("\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Failed to generate GitHub data: {exc}", file=sys.stderr)
        raise
