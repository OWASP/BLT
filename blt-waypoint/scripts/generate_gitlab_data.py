#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://gitlab.com/api/v4"
GROUP = os.getenv("GITLAB_GROUP", "owasp-blt")
OUT = os.getenv("GITLAB_DATA_OUT", "gitlab_data.json")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
CI_JOB_TOKEN = os.getenv("CI_JOB_TOKEN")


def request_json(url):
    headers = {"User-Agent": "blt-waypoint-data-generator"}
    if GITLAB_TOKEN:
        headers["PRIVATE-TOKEN"] = GITLAB_TOKEN
    elif CI_JOB_TOKEN:
        headers["JOB-TOKEN"] = CI_JOB_TOKEN
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8")), resp.headers


def all_pages(url):
    items = []
    page = 1
    while True:
        data, _headers = request_json(f"{url}{'&' if '?' in url else '?'}per_page=100&page={page}")
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
        if exc.code in (401, 403, 404):
            return 0
        raise
    total = headers.get("X-Total")
    if total and total.isdigit():
        return int(total)
    return len(data) if isinstance(data, list) else 0


def optional_json(url, default=None):
    try:
        data, _headers = request_json(url)
        return data
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 404):
            return default
        raise


def project_path(project):
    return urllib.parse.quote_plus(project["path_with_namespace"])


def readme_chars(project):
    path = project_path(project)
    ref = urllib.parse.quote(project.get("default_branch") or "main", safe="")
    for name in ("README.md", "readme.md", "README"):
        file_path = urllib.parse.quote(name, safe="")
        url = f"{API}/projects/{path}/repository/files/{file_path}/raw?ref={ref}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "blt-waypoint-data-generator"})
            if GITLAB_TOKEN:
                req.add_header("PRIVATE-TOKEN", GITLAB_TOKEN)
            elif CI_JOB_TOKEN:
                req.add_header("JOB-TOKEN", CI_JOB_TOKEN)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return len(resp.read().decode("utf-8", "ignore"))
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                return 0
    return 0


def latest_commit(project):
    commits = optional_json(f"{API}/projects/{project_path(project)}/repository/commits?per_page=1", []) or []
    if not commits:
        return None
    c = commits[0]
    return {
        "sha": (c.get("id") or "")[:7],
        "message": (c.get("title") or "").split("\n")[0],
        "author": c.get("author_name"),
        "author_avatar": "",
        "author_html_url": "",
        "html_url": c.get("web_url"),
        "date": c.get("authored_date") or c.get("committed_date"),
    }


def latest_merge_request(project):
    mrs = optional_json(
        f"{API}/projects/{project_path(project)}/merge_requests?scope=all&order_by=updated_at&sort=desc&per_page=1",
        [],
    ) or []
    if not mrs:
        return None
    mr = mrs[0]
    state = "merged" if mr.get("state") == "merged" else mr.get("state")
    return {
        "number": mr.get("iid"),
        "title": mr.get("title"),
        "html_url": mr.get("web_url"),
        "state": state,
        "author": (mr.get("author") or {}).get("username"),
        "author_avatar": (mr.get("author") or {}).get("avatar_url"),
        "author_html_url": (mr.get("author") or {}).get("web_url"),
        "updated_at": mr.get("updated_at"),
    }


def latest_issue(project):
    issues = optional_json(
        f"{API}/projects/{project_path(project)}/issues?state=opened&order_by=updated_at&sort=desc&per_page=1",
        [],
    ) or []
    if not issues:
        return None
    issue = issues[0]
    return {
        "number": issue.get("iid"),
        "title": issue.get("title"),
        "html_url": issue.get("web_url"),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "user": issue.get("author"),
        "labels": [{"name": label, "color": ""} for label in issue.get("labels", [])],
        "assignees": issue.get("assignees", []),
        "linked_prs": [],
        "repo_name": project.get("name"),
        "repo_html_url": project.get("web_url"),
    }


def primary_language(project):
    languages = optional_json(f"{API}/projects/{project_path(project)}/languages", {}) or {}
    if not languages:
        return None
    return max(languages.items(), key=lambda item: item[1])[0]


def contributors(project):
    data = optional_json(f"{API}/projects/{project_path(project)}/repository/contributors?per_page=10", []) or []
    return [
        {
            "login": c.get("name") or c.get("email") or "Contributor",
            "avatar_url": "",
            "contributions": c.get("commits") or 0,
            "html_url": "",
        }
        for c in data
    ]


def latest_release(project):
    releases = optional_json(f"{API}/projects/{project_path(project)}/releases?per_page=1", []) or []
    if releases:
        rel = releases[0]
        return {
            "tag_name": rel.get("tag_name"),
            "name": rel.get("name") or rel.get("tag_name"),
            "html_url": rel.get("_links", {}).get("self") or rel.get("assets", {}).get("links", [{}])[0].get("url") or project.get("web_url"),
            "published_at": rel.get("released_at") or rel.get("created_at"),
        }
    tags = optional_json(f"{API}/projects/{project_path(project)}/repository/tags?per_page=1", []) or []
    if not tags:
        return None
    tag = tags[0]
    return {
        "tag_name": tag.get("name"),
        "name": tag.get("message") or tag.get("name"),
        "html_url": f"{project.get('web_url')}/-/tags/{urllib.parse.quote(tag.get('name') or '', safe='')}",
        "published_at": (tag.get("commit") or {}).get("created_at"),
    }


def normalize_project(project):
    path = project_path(project)
    open_mrs = optional_json(f"{API}/projects/{path}/merge_requests?state=opened&per_page=100", []) or []
    topics = project.get("topics") or project.get("tag_list") or []
    default_branch = project.get("default_branch") or "main"
    return {
        "id": project.get("id"),
        "name": project.get("name"),
        "full_name": project.get("path_with_namespace"),
        "private": project.get("visibility") != "public",
        "html_url": project.get("web_url"),
        "description": project.get("description"),
        "fork": bool(project.get("forked_from_project")),
        "created_at": project.get("created_at"),
        "updated_at": project.get("last_activity_at"),
        "pushed_at": project.get("last_activity_at"),
        "homepage": "",
        "size": ((project.get("statistics") or {}).get("repository_size") or 0) // 1024,
        "stargazers_count": project.get("star_count") or 0,
        "language": primary_language(project),
        "has_pages": False,
        "forks_count": project.get("forks_count") or 0,
        "archived": bool(project.get("archived")),
        "open_issues_count": project.get("open_issues_count") or 0,
        "license": None,
        "topics": topics,
        "visibility": project.get("visibility"),
        "default_branch": default_branch,
        "readme_chars": readme_chars(project),
        "contributors": contributors(project),
        "total_commits": count_items(f"{API}/projects/{path}/repository/commits"),
        "weekly_commits": [],
        "file_count": 0,
        "branch_count": count_items(f"{API}/projects/{path}/repository/branches"),
        "open_pr_count": len(open_mrs),
        "agent_pr_count": 0,
        "latest_issue": latest_issue(project),
        "latest_commit": latest_commit(project),
        "latest_pr": latest_merge_request(project),
        "latest_release": latest_release(project),
        "star_history": [],
        "has_wrangler_toml": optional_json(f"{API}/projects/{path}/repository/files/wrangler.toml?ref={urllib.parse.quote(default_branch, safe='')}", None) is not None,
    }


def main():
    group = urllib.parse.quote_plus(GROUP)
    projects = all_pages(f"{API}/groups/{group}/projects?include_subgroups=false&order_by=last_activity_at&sort=desc&statistics=true")
    repos = [normalize_project(p) for p in projects]
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "gitlab",
        "org": GROUP,
        "cumulative": {
            "total_repos": len(repos),
            "active_repos": sum(1 for r in repos if not r.get("archived")),
            "total_stars": sum(r.get("stargazers_count") or 0 for r in repos),
            "total_forks": sum(r.get("forks_count") or 0 for r in repos),
            "total_open_issues": sum(r.get("open_issues_count") or 0 for r in repos),
            "total_open_prs": sum(r.get("open_pr_count") or 0 for r in repos),
            "total_agent_prs": 0,
            "total_size_kb": sum(r.get("size") or 0 for r in repos),
            "total_topics": len({t for r in repos for t in r.get("topics", [])}),
            "total_languages": 0,
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
        print(f"Failed to generate GitLab data: {exc}", file=sys.stderr)
        raise
