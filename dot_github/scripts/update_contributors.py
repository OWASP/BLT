#!/usr/bin/env python3
"""Update profile/README.md with all-time contributors across all OWASP-BLT org repos.

Contributors are aggregated across every public repository, deduplicated by
login, sorted by total contributions (descending), and rendered as a grid of
linked avatar images in the profile README.

Bot accounts (GitHub type "Bot" or logins ending with "[bot]", such as
dependabot[bot]) are excluded from the output.
"""

import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

import requests

ORG = "OWASP-BLT"
README_PATH = "profile/README.md"
AVATAR_LINK_STYLE = 'style="display:inline-block; margin:0 6px 6px 0;"'

CONTRIBUTORS_START = "<!-- CONTRIBUTORS-START -->"
CONTRIBUTORS_END = "<!-- CONTRIBUTORS-END -->"

WAITING_START = "<!-- WAITING-CONTRIBUTORS-START -->"
WAITING_END = "<!-- WAITING-CONTRIBUTORS-END -->"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

session = requests.Session()
session.headers.update(
    {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
)


def get_all_repos():
    """Return all public repos in the org."""
    repos = []
    page = 1
    while True:
        resp = session.get(
            f"https://api.github.com/orgs/{ORG}/repos",
            params={"per_page": 100, "page": page, "type": "public"},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos


def get_repo_contributors(repo_name):
    """Return all non-anonymous contributors for *repo_name* as a list of dicts."""
    contributors = []
    page = 1
    while True:
        resp = session.get(
            f"https://api.github.com/repos/{ORG}/{repo_name}/contributors",
            params={"per_page": 100, "page": page},
        )
        if resp.status_code == 204:
            break  # Empty repository
        if resp.status_code != 200:
            print(
                f"  Warning: could not fetch contributors for {repo_name}: "
                f"HTTP {resp.status_code}"
            )
            break
        data = resp.json()
        if not data:
            break
        contributors.extend(data)
        if len(data) < 100:
            break
        page += 1
    return contributors


def aggregate_contributors(repos):
    """Aggregate contributors across all repos, sorted by total contributions desc.

    Returns a list of dicts with keys: login, avatar_url, html_url, contributions.
    Bot accounts (GitHub type "Bot" or logins ending with "[bot]") are excluded.
    """
    totals = {}  # login -> contributor dict
    for repo in repos:
        name = repo["name"]
        print(f"  Fetching contributors for {name}…")
        for c in get_repo_contributors(name):
            if c.get("type") == "Bot":
                continue
            login = c.get("login")
            if not login:
                continue
            if login.endswith("[bot]"):
                continue
            if login not in totals:
                totals[login] = {
                    "login": login,
                    "avatar_url": c.get("avatar_url", ""),
                    "html_url": c.get("html_url", f"https://github.com/{login}"),
                    "contributions": 0,
                }
            totals[login]["contributions"] += c.get("contributions", 0)

    return sorted(totals.values(), key=lambda x: x["contributions"], reverse=True)


def get_open_pr_authors(repos, contributor_logins):
    """Return authors of open PRs who have not yet had a contribution merged.

    Iterates over all repos, collects open PR authors, and excludes anyone
    already present in *contributor_logins*.  Bot accounts are filtered out.

    Returns a list of dicts with keys: login, avatar_url, html_url, pr_count,
    sorted by pr_count descending.
    """
    authors = {}  # login -> dict
    for repo in repos:
        name = repo["name"]
        print(f"  Fetching open PRs for {name}…")
        page = 1
        while True:
            resp = session.get(
                f"https://api.github.com/repos/{ORG}/{name}/pulls",
                params={"state": "open", "per_page": 100, "page": page},
            )
            if resp.status_code != 200:
                print(
                    f"  Warning: could not fetch PRs for {name}: "
                    f"HTTP {resp.status_code}"
                )
                break
            data = resp.json()
            if not data:
                break
            for pr in data:
                user = pr.get("user")
                if not user:
                    continue
                if user.get("type") == "Bot":
                    continue
                login = user.get("login", "")
                if not login or login.endswith("[bot]"):
                    continue
                if login in contributor_logins:
                    continue  # already a contributor – skip
                if login not in authors:
                    authors[login] = {
                        "login": login,
                        "avatar_url": user.get("avatar_url", ""),
                        "html_url": user.get(
                            "html_url", f"https://github.com/{login}"
                        ),
                        "pr_count": 0,
                    }
                authors[login]["pr_count"] += 1
            if len(data) < 100:
                break
            page += 1

    return sorted(authors.values(), key=lambda x: x["pr_count"], reverse=True)


def build_contributors_section(contributors):
    """Return the full markdown/HTML section string for *contributors*."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    count = len(contributors)

    # Inline avatar links – flow naturally in GitHub-rendered markdown
    parts = []
    for c in contributors:
        login = c["login"]
        url = c["html_url"]
        avatar = c["avatar_url"]
        contribs = c["contributions"]
        # Request a 60 px thumbnail from GitHub's avatar CDN (displayed at 50 px)
        parsed = urlparse(avatar)
        params = parse_qs(parsed.query)
        params["v"] = ["4"]
        params["s"] = ["60"]
        avatar_url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
        parts.append(
            f'<a href="{url}" title="{login}: {contribs} contributions" '
            f'{AVATAR_LINK_STYLE}>'
            f'<img src="{avatar_url}" width="50" height="50" alt="{login}">'
            f"</a>"
        )

    avatars_html = build_avatar_grid(parts)

    return (
        f"{CONTRIBUTORS_START}\n"
        f"## 👥 All-Time Contributors ({count} total)\n\n"
        f"*Last updated: {timestamp} — sorted by total contributions across all repositories*\n\n"
        f"{avatars_html}\n\n"
        f"{CONTRIBUTORS_END}"
    )


def build_waiting_section(waiting):
    """Return the markdown/HTML section for PR authors waiting to be merged."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    count = len(waiting)

    parts = []
    for c in waiting:
        login = c["login"]
        avatar = c["avatar_url"]
        pr_count = c["pr_count"]
        parsed = urlparse(avatar)
        params = parse_qs(parsed.query)
        params["v"] = ["4"]
        params["s"] = ["60"]
        avatar_url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
        pr_url = (
            f"https://github.com/pulls?q=is%3Apr+is%3Aopen+"
            f"org%3A{ORG}+author%3A{login}"
        )
        parts.append(
            f'<a href="{pr_url}" title="{login}: {pr_count} open PR(s) waiting" '
            f'{AVATAR_LINK_STYLE}>'
            f'<img src="{avatar_url}" width="50" height="50" alt="{login}">'
            f"</a>"
        )

    avatars_html = (
        build_avatar_grid(parts)
        if parts
        else "*No contributors currently waiting to be merged.*"
    )

    return (
        f"{WAITING_START}\n"
        f"## ⏳ Contributors with PRs Waiting to be Merged ({count} total)\n\n"
        f"*Last updated: {timestamp} — open PRs from contributors who have not yet had a contribution merged*\n\n"
        f"{avatars_html}\n\n"
        f"{WAITING_END}"
    )


def _replace_section(content, start_marker, end_marker, new_section):
    """Replace a marked section in *content*, or append if markers are absent."""
    if start_marker in content and end_marker in content:
        pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
        return re.sub(pattern, new_section, content, flags=re.DOTALL)
    return content.rstrip() + "\n\n" + new_section + "\n"


def build_avatar_grid(parts, columns=10):
    """Return avatar links arranged in horizontal rows that wrap."""
    rows = []
    for i in range(0, len(parts), columns):
        row_cells = "".join(f"<td>{part}</td>" for part in parts[i : i + columns])
        rows.append(f"<tr>{row_cells}</tr>")
    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def update_readme(contributors_section, waiting_section):
    """Insert or replace both contributor sections in the README."""
    with open(README_PATH, "r", encoding="utf-8") as fh:
        content = fh.read()

    content = _replace_section(
        content, CONTRIBUTORS_START, CONTRIBUTORS_END, contributors_section
    )
    content = _replace_section(
        content, WAITING_START, WAITING_END, waiting_section
    )

    with open(README_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)


if __name__ == "__main__":
    repos = get_all_repos()
    print(f"Found {len(repos)} public repositories in {ORG}")

    print("Aggregating contributors across all repositories…")
    contributors = aggregate_contributors(repos)
    print(f"Found {len(contributors)} unique contributors")

    contributor_logins = {c["login"] for c in contributors}

    print("Fetching open PRs to find contributors waiting to be merged…")
    waiting = get_open_pr_authors(repos, contributor_logins)
    print(f"Found {len(waiting)} contributors with open PRs waiting to be merged")

    contributors_section = build_contributors_section(contributors)
    waiting_section = build_waiting_section(waiting)
    update_readme(contributors_section, waiting_section)
    print(
        f"README updated — {len(contributors)} contributors, "
        f"{len(waiting)} waiting."
    )