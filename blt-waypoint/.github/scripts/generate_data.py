#!/usr/bin/env python3
"""
Fetch all OWASP-BLT org repos from the GitHub REST API and write data.json.

Environment variables:
  GH_TOKEN  – GitHub personal access token or GITHUB_TOKEN (optional but
               strongly recommended to avoid the 60 req/hr unauthenticated limit)
  ORG       – GitHub organisation name (default: OWASP-BLT)
  OUT_FILE  – output path (default: data.json)
"""

import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

ORG      = os.environ.get("ORG", "OWASP-BLT")
OUT_FILE = os.environ.get("OUT_FILE", "data.json")
TOKEN    = os.environ.get("GH_TOKEN", "")
API_BASE = "https://api.github.com"
PER_PAGE = 100


def make_request(url: str) -> object:
    """Make an authenticated GET request and return parsed JSON."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            if not body:
                return None
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"HTTP {exc.code} fetching {url}: {body[:200]}", file=sys.stderr)
        raise
    except urllib.error.URLError as exc:
        print(f"Network error fetching {url}: {exc.reason}", file=sys.stderr)
        raise


def fetch_all_pages(path: str) -> list:
    """Fetch every page of a paginated GitHub endpoint."""
    results = []
    page = 1
    sep = "&" if "?" in path else "?"
    while True:
        url = f"{API_BASE}{path}{sep}per_page={PER_PAGE}&page={page}"
        data = make_request(url)
        if not isinstance(data, list) or not data:
            break
        results.extend(data)
        if len(data) < PER_PAGE:
            break
        page += 1
        # Be polite – avoid secondary rate-limit bursts
        time.sleep(0.1)
    return results


def fetch_readme_chars(repo_full_name: str) -> int:
    """Return the character count of the README for a single repo (0 if none)."""
    try:
        data = make_request(f"{API_BASE}/repos/{repo_full_name}/readme")
        content = data.get("content", "")
        encoding = data.get("encoding", "base64")
        if encoding == "base64":
            decoded = base64.b64decode(content).decode("utf-8", errors="replace")
        else:
            decoded = content
        return len(decoded)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return 0
        print(f"  Warning: could not fetch README for {repo_full_name}: {exc}", file=sys.stderr)
        return 0
    except (urllib.error.URLError, Exception) as exc:
        print(f"  Warning: could not fetch README for {repo_full_name}: {exc}", file=sys.stderr)
        return 0


def fetch_languages(repo_full_name: str) -> dict:
    """Return the language breakdown (bytes) for a single repo."""
    try:
        return make_request(f"{API_BASE}/repos/{repo_full_name}/languages")
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"  Warning: could not fetch languages for {repo_full_name}: {exc}", file=sys.stderr)
        return {}


def fetch_contributors(repo_full_name: str, top_n: int = 10) -> tuple[list[dict], int]:
    """Return (top_n contributors, total_commits) for a repo.

    All contributor pages are fetched so that total_commits reflects the full
    commit history, while only the top_n entries are included in the returned list.
    """
    try:
        all_contributors = fetch_all_pages(
            f"/repos/{repo_full_name}/contributors?anon=false"
        )
        if not isinstance(all_contributors, list):
            return [], 0
        total_commits = sum(c.get("contributions", 0) for c in all_contributors)
        top = [
            {
                "login": c.get("login", ""),
                "avatar_url": c.get("avatar_url", ""),
                "contributions": c.get("contributions", 0),
                "html_url": c.get("html_url", ""),
            }
            for c in all_contributors[:top_n]
        ]
        return top, total_commits
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"  Warning: could not fetch contributors for {repo_full_name}: {exc}", file=sys.stderr)
        return [], 0


def fetch_file_count(repo_full_name: str, default_branch: str) -> int:
    """Return the total number of files (blobs) in the repo's default branch tree."""
    try:
        branch_data = make_request(
            f"{API_BASE}/repos/{repo_full_name}/branches/{default_branch}"
        )
        tree_sha = (
            branch_data.get("commit", {})
            .get("commit", {})
            .get("tree", {})
            .get("sha", "")
        )
        if not tree_sha:
            return 0
        tree_data = make_request(
            f"{API_BASE}/repos/{repo_full_name}/git/trees/{tree_sha}?recursive=1"
        )
        blobs = [
            item for item in tree_data.get("tree", []) if item.get("type") == "blob"
        ]
        return len(blobs)
    except (urllib.error.HTTPError, urllib.error.URLError, Exception) as exc:
        print(f"  Warning: could not fetch file count for {repo_full_name}: {exc}", file=sys.stderr)
        return 0


def fetch_branch_count(repo_full_name: str) -> int:
    """Return the total number of branches for a repo."""
    try:
        branches = fetch_all_pages(f"/repos/{repo_full_name}/branches")
        return len(branches)
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"  Warning: could not fetch branches for {repo_full_name}: {exc}", file=sys.stderr)
        return 0


def fetch_pr_counts(repo_full_name: str) -> tuple[int, int]:
    """Return (open_pr_count, agent_pr_count) for a repo.

    agent_pr_count is the number of open PRs authored by GitHub bots/agents.
    """
    try:
        prs = fetch_all_pages(f"/repos/{repo_full_name}/pulls?state=open")
        total = len(prs)
        agent = sum(1 for pr in prs if pr.get("user", {}).get("type") == "Bot")
        return total, agent
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"  Warning: could not fetch PR counts for {repo_full_name}: {exc}", file=sys.stderr)
        return 0, 0


def fetch_latest_issue(repo_full_name: str) -> dict | None:
    """Return the most recent open issue for a repo, or None if there are none."""
    try:
        data = make_request(
            f"{API_BASE}/repos/{repo_full_name}/issues?state=open&sort=created&direction=desc&per_page=5"
        )
        if not isinstance(data, list) or not data:
            return None
        # The issues API also returns pull requests; skip them
        for issue in data:
            if not issue.get("pull_request"):
                return {
                    "number": issue.get("number"),
                    "title": issue.get("title", ""),
                    "html_url": issue.get("html_url", ""),
                }
        return None
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"  Warning: could not fetch latest issue for {repo_full_name}: {exc}", file=sys.stderr)
        return None


def fetch_weekly_commits(repo_full_name: str, weeks: int = 26) -> list:
    """Return the last `weeks` weekly commit totals as a list of ints."""
    try:
        data = make_request(f"{API_BASE}/repos/{repo_full_name}/stats/commit_activity")
        if not isinstance(data, list):
            return []
        return [w.get("total", 0) for w in data[-weeks:]]
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        if hasattr(exc, "code") and exc.code == 202:
            # GitHub is still computing the stats; return empty for now
            return []
        print(f"  Warning: could not fetch commit activity for {repo_full_name}: {exc}", file=sys.stderr)
        return []


def fetch_latest_commit(repo_full_name: str, default_branch: str) -> dict | None:
    """Return the most recent commit (message, author, sha, url, date) for a repo."""
    try:
        data = make_request(
            f"{API_BASE}/repos/{repo_full_name}/commits?sha={default_branch}&per_page=1"
        )
        if not isinstance(data, list) or not data:
            return None
        commit = data[0]
        commit_detail = commit.get("commit", {})
        message_full = commit_detail.get("message", "")
        message = message_full.split("\n")[0][:120]
        author_obj = commit_detail.get("author") or {}
        github_author = commit.get("author") or {}
        author = author_obj.get("name", "")
        if not author:
            author = github_author.get("login", "")
        author_avatar = github_author.get("avatar_url", "")
        author_html_url = github_author.get("html_url", "")
        return {
            "sha": commit.get("sha", "")[:7],
            "message": message,
            "author": author,
            "author_avatar": author_avatar,
            "author_html_url": author_html_url,
            "html_url": commit.get("html_url", ""),
            "date": author_obj.get("date", ""),
        }
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            return None
        print(f"  Warning: could not fetch latest commit for {repo_full_name}: {exc}", file=sys.stderr)
        return None
    except (urllib.error.URLError, Exception) as exc:
        print(f"  Warning: could not fetch latest commit for {repo_full_name}: {exc}", file=sys.stderr)
        return None


def fetch_latest_pr(repo_full_name: str) -> dict | None:
    """Return the most recent PR (any state) for a repo, including merged status."""
    try:
        data = make_request(
            f"{API_BASE}/repos/{repo_full_name}/pulls?state=all&sort=updated&direction=desc&per_page=1"
        )
        if not isinstance(data, list) or not data:
            return None
        pr = data[0]
        user = pr.get("user") or {}
        state = pr.get("state", "open")
        merged_at = pr.get("merged_at")
        if merged_at:
            state = "merged"
        return {
            "number": pr.get("number"),
            "title": pr.get("title", ""),
            "html_url": pr.get("html_url", ""),
            "state": state,
            "author": user.get("login", ""),
            "author_avatar": user.get("avatar_url", ""),
            "author_html_url": user.get("html_url", ""),
            "updated_at": pr.get("updated_at", ""),
        }
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"  Warning: could not fetch latest PR for {repo_full_name}: {exc}", file=sys.stderr)
        return None


def fetch_has_wrangler_toml(repo_full_name: str, default_branch: str) -> bool:
    """Return True if the repo contains a wrangler.toml in its root directory."""
    try:
        make_request(
            f"{API_BASE}/repos/{repo_full_name}/contents/wrangler.toml?ref={default_branch}"
        )
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        print(f"  Warning: could not check wrangler.toml for {repo_full_name}: {exc}", file=sys.stderr)
        return False
    except (urllib.error.URLError, Exception) as exc:
        print(f"  Warning: could not check wrangler.toml for {repo_full_name}: {exc}", file=sys.stderr)
        return False


def fetch_latest_release(repo_full_name: str) -> dict | None:
    """Return the latest release for a repo, or None if there are none."""
    try:
        data = make_request(f"{API_BASE}/repos/{repo_full_name}/releases/latest")
        return {
            "tag_name": data.get("tag_name", ""),
            "name": data.get("name", ""),
            "html_url": data.get("html_url", ""),
            "published_at": data.get("published_at", ""),
        }
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        print(f"  Warning: could not fetch latest release for {repo_full_name}: {exc}", file=sys.stderr)
        return None
    except (urllib.error.URLError, Exception) as exc:
        print(f"  Warning: could not fetch latest release for {repo_full_name}: {exc}", file=sys.stderr)
        return None


def fetch_star_history(repo_full_name: str, weeks: int = 26) -> list:
    """Return per-week new-star counts for the last `weeks` weeks as a list of ints."""
    try:
        all_starred = []
        page = 1
        while True:
            url = f"{API_BASE}/repos/{repo_full_name}/stargazers?per_page={PER_PAGE}&page={page}"
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/vnd.github.star+json")
            req.add_header("X-GitHub-Api-Version", "2022-11-28")
            if TOKEN:
                req.add_header("Authorization", f"Bearer {TOKEN}")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return []
                raise
            if not isinstance(data, list) or not data:
                break
            all_starred.extend(data)
            if len(data) < PER_PAGE:
                break
            page += 1
            time.sleep(0.1)

        now = datetime.now(timezone.utc)
        counts = [0] * weeks
        for star in all_starred:
            starred_at = star.get("starred_at", "")
            if not starred_at:
                continue
            try:
                ts = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            week_idx = int((now - ts).total_seconds() // (7 * 86400))
            if 0 <= week_idx < weeks:
                counts[weeks - 1 - week_idx] += 1
        return counts
    except (urllib.error.HTTPError, urllib.error.URLError, Exception) as exc:
        print(f"  Warning: could not fetch star history for {repo_full_name}: {exc}", file=sys.stderr)
        return []


def main() -> None:
    print(f"Fetching repos for org: {ORG}", flush=True)
    repos = fetch_all_pages(f"/orgs/{ORG}/repos")
    print(f"  → {len(repos)} repos", flush=True)

    # ------------------------------------------------------------------ #
    # Cumulative stats – aggregate over all repos                         #
    # ------------------------------------------------------------------ #
    total_stars    = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks    = sum(r.get("forks_count", 0) for r in repos)
    total_issues   = sum(r.get("open_issues_count", 0) for r in repos)
    total_size_kb  = sum(r.get("size", 0) for r in repos)
    active_repos   = sum(1 for r in repos if not r.get("archived") and not r.get("fork"))
    all_topics = set()
    for repo in repos:
        for t in repo.get("topics") or []:
            all_topics.add(t)

    # Aggregate language bytes across all repos
    print("Fetching language breakdowns…", flush=True)
    all_lang_bytes: dict[str, int] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            continue
        langs = fetch_languages(repo["full_name"])
        for lang, count in langs.items():
            all_lang_bytes[lang] = all_lang_bytes.get(lang, 0) + count
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch README character counts for each repo
    print("Fetching README character counts…", flush=True)
    readme_chars_map: dict[str, int] = {}
    for i, repo in enumerate(repos):
        chars = fetch_readme_chars(repo["full_name"])
        readme_chars_map[repo["full_name"]] = chars
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch top contributors and weekly commit activity for each non-archived repo
    print("Fetching contributors and commit activity…", flush=True)
    contributors_map: dict[str, list] = {}
    total_commits_map: dict[str, int] = {}
    weekly_commits_map: dict[str, list] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            contributors_map[repo["full_name"]] = []
            total_commits_map[repo["full_name"]] = 0
            weekly_commits_map[repo["full_name"]] = []
        else:
            top_contributors, total_commits = fetch_contributors(repo["full_name"])
            contributors_map[repo["full_name"]] = top_contributors
            total_commits_map[repo["full_name"]] = total_commits
            weekly_commits_map[repo["full_name"]] = fetch_weekly_commits(repo["full_name"])
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch recursive file count for each non-archived repo
    print("Fetching file counts…", flush=True)
    file_count_map: dict[str, int] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            file_count_map[repo["full_name"]] = 0
        else:
            file_count_map[repo["full_name"]] = fetch_file_count(
                repo["full_name"], repo.get("default_branch", "main")
            )
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch branch counts for each non-archived repo
    print("Fetching branch counts…", flush=True)
    branch_count_map: dict[str, int] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            branch_count_map[repo["full_name"]] = 0
        else:
            branch_count_map[repo["full_name"]] = fetch_branch_count(repo["full_name"])
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch open PR counts for each non-archived repo
    print("Fetching open PR counts…", flush=True)
    open_pr_count_map: dict[str, int] = {}
    agent_pr_count_map: dict[str, int] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            open_pr_count_map[repo["full_name"]] = 0
            agent_pr_count_map[repo["full_name"]] = 0
        else:
            total_prs, agent_prs = fetch_pr_counts(repo["full_name"])
            open_pr_count_map[repo["full_name"]] = total_prs
            agent_pr_count_map[repo["full_name"]] = agent_prs
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch the most recent open issue for each non-archived repo
    print("Fetching latest issues…", flush=True)
    latest_issue_map: dict[str, dict | None] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            latest_issue_map[repo["full_name"]] = None
        else:
            latest_issue_map[repo["full_name"]] = fetch_latest_issue(repo["full_name"])
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch per-week star counts for each non-archived repo
    print("Fetching star history…", flush=True)
    star_history_map: dict[str, list] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            star_history_map[repo["full_name"]] = []
        else:
            star_history_map[repo["full_name"]] = fetch_star_history(repo["full_name"])
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch the most recent commit for each non-archived repo
    print("Fetching latest commits…", flush=True)
    latest_commit_map: dict[str, dict | None] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            latest_commit_map[repo["full_name"]] = None
        else:
            latest_commit_map[repo["full_name"]] = fetch_latest_commit(
                repo["full_name"], repo.get("default_branch", "main")
            )
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch the most recent PR for each non-archived repo
    print("Fetching latest PRs…", flush=True)
    latest_pr_map: dict[str, dict | None] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            latest_pr_map[repo["full_name"]] = None
        else:
            latest_pr_map[repo["full_name"]] = fetch_latest_pr(repo["full_name"])
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Fetch the latest release for each non-archived repo
    print("Fetching latest releases…", flush=True)
    latest_release_map: dict[str, dict | None] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            latest_release_map[repo["full_name"]] = None
        else:
            latest_release_map[repo["full_name"]] = fetch_latest_release(repo["full_name"])
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Check for wrangler.toml in each non-archived repo
    print("Checking for wrangler.toml…", flush=True)
    has_wrangler_toml_map: dict[str, bool] = {}
    for i, repo in enumerate(repos):
        if repo.get("archived"):
            has_wrangler_toml_map[repo["full_name"]] = False
        else:
            has_wrangler_toml_map[repo["full_name"]] = fetch_has_wrangler_toml(
                repo["full_name"], repo.get("default_branch", "main")
            )
            time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(repos)} done", flush=True)

    # Language counts (how many repos use each language as primary)
    lang_repo_count: dict[str, int] = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            lang_repo_count[lang] = lang_repo_count.get(lang, 0) + 1

    # Trim repo objects to the fields the dashboard actually needs
    # (keeps data.json small)
    KEEP_FIELDS = {
        "id", "name", "full_name", "description", "html_url", "homepage",
        "language", "stargazers_count", "forks_count", "open_issues_count",
        "fork", "archived", "private", "topics",
        "default_branch", "updated_at", "created_at", "pushed_at",
        "license", "visibility", "size", "has_pages",
    }
    slim_repos = sorted(
        [
            {**{k: v for k, v in repo.items() if k in KEEP_FIELDS},
             "readme_chars": readme_chars_map.get(repo["full_name"], 0),
             "contributors": contributors_map.get(repo["full_name"], []),
             "total_commits": total_commits_map.get(repo["full_name"], 0),
             "weekly_commits": weekly_commits_map.get(repo["full_name"], []),
             "file_count": file_count_map.get(repo["full_name"], 0),
             "branch_count": branch_count_map.get(repo["full_name"], 0),
             "open_pr_count": open_pr_count_map.get(repo["full_name"], 0),
             "agent_pr_count": agent_pr_count_map.get(repo["full_name"], 0),
             "latest_issue": latest_issue_map.get(repo["full_name"]),
             "latest_commit": latest_commit_map.get(repo["full_name"]),
             "latest_pr": latest_pr_map.get(repo["full_name"]),
             "latest_release": latest_release_map.get(repo["full_name"]),
             "star_history": star_history_map.get(repo["full_name"], []),
             "has_wrangler_toml": has_wrangler_toml_map.get(repo["full_name"], False)}
            for repo in repos
        ],
        key=lambda r: r.get("updated_at", ""),
        reverse=True,
    )

    total_readme_chars = sum(readme_chars_map.values())
    total_branches = sum(branch_count_map.values())
    total_open_prs = sum(open_pr_count_map.values())
    total_agent_prs = sum(agent_pr_count_map.values())
    # GitHub's open_issues_count includes PRs; subtract to get true issue count
    total_issues = total_issues - total_open_prs

    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "org": ORG,
        "cumulative": {
            "total_repos":        len(repos),
            "active_repos":       active_repos,
            "total_stars":        total_stars,
            "total_forks":        total_forks,
            "total_open_issues":  total_issues,
            "total_open_prs":     total_open_prs,
            "total_agent_prs":    total_agent_prs,
            "total_size_kb":      total_size_kb,
            "total_topics":       len(all_topics),
            "total_languages":    len(all_lang_bytes),
            "total_readme_chars": total_readme_chars,
            "total_branches":     total_branches,
            "lang_bytes":         dict(
                sorted(all_lang_bytes.items(), key=lambda x: x[1], reverse=True)
            ),
            "lang_repo_count":    dict(
                sorted(lang_repo_count.items(), key=lambda x: x[1], reverse=True)
            ),
        },
        "repos": slim_repos,
    }

    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(OUT_FILE) / 1024
    print(f"Wrote {OUT_FILE} ({size_kb:.1f} KB)", flush=True)


if __name__ == "__main__":
    main()
