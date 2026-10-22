#!/usr/bin/env python3
"""
Fetch every repository in the OWASP GitHub organization and write the data the Bumper page
(public/index.html) shows: public/data/repos.json. Standard library only.

    GITHUB_TOKEN=... python3 generate_repo_list.py   # full data: GraphQL, 25 repos per request (~60, ~5 min)
    python3 generate_repo_list.py                    # no token: REST repo list (~15 requests)

Both also look up reminder issues (2 searches, plus one request per reminder with replies).
Environment: GITHUB_ORG (owasp), OUTPUT_FILE (public/data/repos.json).
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List
import urllib.parse
import urllib.request
import urllib.error


def parse_yaml_frontmatter(content: str) -> Dict:
    """Parse YAML front matter from markdown content."""
    result = {
        "title": "",
        "tags": [],
        "level": None,
        "pitch": "",
        "type": "",
        "region": "",
        "country": ""
    }
    
    # Check if content starts with ---
    if not content.strip().startswith('---'):
        return result
    
    # Find the closing ---
    lines = content.split('\n')
    in_frontmatter = False
    frontmatter_lines = []
    
    for line in lines:
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break
        if in_frontmatter:
            frontmatter_lines.append(line)
    
    frontmatter_text = '\n'.join(frontmatter_lines)
    
    # Parse key-value pairs (simple YAML parsing without external library)
    for line in frontmatter_lines:
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip().lower()
            value = value.strip()
            
            if key == 'title':
                result['title'] = value
            elif key == 'tags':
                # Handle both inline tags and list format
                if value:
                    # Handle [tag1, tag2] format
                    if value.startswith('[') and value.endswith(']'):
                        value = value[1:-1]
                    result['tags'] = [t.strip().strip('"\'') for t in value.split(',') if t.strip()]
            elif key == 'level':
                try:
                    result['level'] = float(value)
                except (ValueError, TypeError):
                    pass
            elif key == 'pitch':
                result['pitch'] = value
            elif key == 'type':
                result['type'] = value
            elif key == 'region':
                result['region'] = value
            elif key == 'country':
                result['country'] = value
    
    return result


# With a token, one GraphQL query returns everything the page shows for 25 repos (about 60
# requests and ~5 minutes for the whole org) instead of 4 REST calls per repo. GitHub stops a
# query after about 10 seconds (502/504), so a page that times out is retried at half the size,
# which then stays the ceiling for the rest of the run.
REPO_QUERY = """
query($org: String!, $cursor: String, $size: Int!) {
  organization(login: $org) {
    repositories(first: $size, after: $cursor, orderBy: {field: PUSHED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name description url homepageUrl stargazerCount forkCount createdAt updatedAt pushedAt
        isArchived isFork isTemplate hasIssuesEnabled diskUsage
        primaryLanguage { name }
        repositoryTopics(first: 10) { nodes { topic { name } } }
        issues(states: OPEN) { totalCount }
        pullRequests(states: OPEN) { totalCount }
        defaultBranchRef { target { ... on Commit { history(first: 5) { nodes { committedDate messageHeadline author { name user { login url } } } } } } }
        indexMd: object(expression: "HEAD:index.md") { ... on Blob { text } }
      }
    }
  }
}
"""


def _graphql(query: str, variables: Dict, token: str) -> Dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    headers = {"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "OWASP-Bumper-Repo-List-Generator"}
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode())
    if data.get("errors") and not data.get("data"):
        raise RuntimeError(data["errors"])
    return data["data"]


# Commit authors that are automation, not maintainers (same list as public/bumper.js).
BOT = re.compile(r"\[bot\]$|^(dependabot|renovate|github-actions|owasp-?bot|owasp-nest|snyk-bot|allcontributors)|bot$", re.I)


def _author(commit: Dict) -> str:
    author = commit.get("author") or {}
    return (author.get("user") or {}).get("login") or author.get("name", "")


def _rest_shape(node: Dict) -> Dict:
    """A GraphQL repository node in the REST field names repo_record() reads."""
    history = (((node.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}).get("nodes") or []
    commit = history[0] if history else {}
    author = commit.get("author") or {}
    user = author.get("user") or {}
    # Upkeep is the last commit by a person. When the last 5 are all bots, the person's commit is
    # older than the 5th, so that date is the most recent it can be.
    humans = [c for c in history if not BOT.search(_author(c))]
    human_at = (humans[0] if humans else history[-1]).get("committedDate", "") if history else ""
    index_text = (node.get("indexMd") or {}).get("text") or ""
    return {
        "name": node.get("name", ""),
        "description": node.get("description") or "",
        "html_url": node.get("url", ""),
        "homepage": node.get("homepageUrl") or "",
        "stargazers_count": node.get("stargazerCount", 0),
        "forks_count": node.get("forkCount", 0),
        "open_issues_count": (node.get("issues") or {}).get("totalCount", 0),
        "open_prs_count": (node.get("pullRequests") or {}).get("totalCount", 0),
        "created_at": node.get("createdAt", ""),
        "updated_at": node.get("updatedAt", ""),
        "pushed_at": node.get("pushedAt", ""),
        "language": (node.get("primaryLanguage") or {}).get("name", ""),
        "topics": [n["topic"]["name"] for n in (node.get("repositoryTopics") or {}).get("nodes", [])],
        "archived": node.get("isArchived", False),
        "fork": node.get("isFork", False),
        "is_template": node.get("isTemplate", False),
        "has_issues": node.get("hasIssuesEnabled", True),
        "size": node.get("diskUsage"),
        "last_commit": {
            "message": commit.get("messageHeadline", ""),
            "author": user.get("login") or author.get("name", ""),
            "author_url": user.get("url", ""),
            "date": commit.get("committedDate", ""),
        } if commit else {},
        "index_md": parse_yaml_frontmatter(index_text) if index_text else {},
        "human_at": human_at,
        "bot_only": bool(history) and not humans,
    }


def fetch_repos_graphql(org: str, token: str, size: int = 25) -> List[Dict]:
    repos, cursor, failures, ceiling = [], None, 0, size
    while True:
        try:
            page = _graphql(REPO_QUERY, {"org": org, "cursor": cursor, "size": size}, token)["organization"]["repositories"]
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            failures += 1
            if failures > 6:
                raise
            ceiling = size = max(5, size // 2)
            print(f"  page failed ({exc}); retrying with {size} repos per page", file=sys.stderr)
            time.sleep(2)
            continue
        failures = 0
        repos.extend(_rest_shape(n) for n in page["nodes"] if n)
        print(f"  {len(repos)} repositories ({size} per page)")
        if not page["pageInfo"]["hasNextPage"]:
            return repos
        cursor = page["pageInfo"]["endCursor"]
        size = min(ceiling, size + 10)


def fetch_repos(org: str, token: str = None) -> List[Dict]:
    """All repositories in the org through REST (100 per request): the fallback without a token,
    which has no PR counts, last commit or index.md."""
    repos = []
    page = 1
    per_page = 100
    
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page={per_page}&page={page}&sort=updated&direction=desc"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OWASP-Bumper-Repo-List-Generator"
        }
        
        if token:
            headers["Authorization"] = f"token {token}"
        
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
                if not data:
                    break
                
                repos.extend(data)
                page += 1
                
                # Check if we've reached the last page
                if len(data) < per_page:
                    break
                    
        except urllib.error.HTTPError as e:
            print(f"Error fetching repositories: {e}", file=sys.stderr)
            print(f"Response: {e.read().decode()}", file=sys.stderr)
            sys.exit(1)
    
    return repos

# Titles of issues that ask whether a repo is maintained: Bumper's own reminders (old and current
# title) and ones people opened by hand. An open one means the repo is waiting on its maintainers.
REMINDER_QUERIES = ['"Repository Activity Reminder"', '"still maintained"']


def _get_json(url: str, token: str = None, timeout: int = 20):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "OWASP-Bumper-Repo-List-Generator"}
    if token:
        headers["Authorization"] = f"token {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
        return json.loads(response.read().decode())


def fetch_last_reply(owner: str, repo: str, number: int, count: int, token: str = None) -> Dict:
    """Author and date of an issue's last comment (one request: page `count` of 1 per page)."""
    try:
        items = _get_json(f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments?per_page=1&page={count}", token)
    except Exception as exc:
        print(f"Warning: comments for {repo}#{number} failed: {exc}", file=sys.stderr)
        return {}
    if not items:
        return {}
    c = items[-1]
    return {"author": (c.get("user") or {}).get("login", ""), "date": c.get("created_at", ""), "url": c.get("html_url", "")}


def fetch_reminders(org: str, token: str = None) -> Dict[str, Dict]:
    """Each repo's latest reminder issue (open or closed), with its replies and how many reminders
    the repo has had in all. A few requests."""
    found: Dict[str, Dict] = {}
    seen: Dict[str, set] = {}
    for phrase in REMINDER_QUERIES:
        q = urllib.parse.quote(f"org:{org} is:issue in:title {phrase}")
        for page in range(1, 11):
            url = f"https://api.github.com/search/issues?q={q}&per_page=100&page={page}&sort=created&order=desc"
            try:
                items = _get_json(url, token).get("items", [])
            except Exception as exc:
                print(f"Warning: reminder search failed ({phrase}): {exc}", file=sys.stderr)
                break
            for item in items:
                name = item.get("repository_url", "").rsplit("/", 1)[-1]
                seen.setdefault(name, set()).add(item.get("number"))
                prev = found.get(name)
                # Prefer an open reminder over a closed one, then the newest.
                key = (item.get("state") == "open", item.get("created_at", ""))
                if name and (not prev or key > (prev["state"] == "open", prev["created"])):
                    found[name] = {
                        "number": item.get("number"), "url": item.get("html_url", ""), "created": item.get("created_at", ""),
                        "state": item.get("state", ""), "closed": item.get("closed_at") or "", "replies": item.get("comments", 0),
                        "author": (item.get("user") or {}).get("login", ""),
                    }
            if len(items) < 100:
                break
    for name, rem in found.items():
        rem["bumps"] = len(seen.get(name, ()))
        if rem["replies"]:
            rem["last_reply"] = fetch_last_reply(org, name, rem["number"], rem["replies"], token)
    return found


# A repo's GitHub homepage (About -> Website) set to its owasp.org project page links the repo to
# that project. Maintainers control it, so it is how a leader fixes Bumper's mapping.
PROJECT_PAGE = re.compile(r"^https?://(?:www\.)?owasp\.org/(?:projects/|www-project-)([a-z0-9-]+)/?$", re.I)
# A repo topic that keeps Bumper from offering reminders for it.
OPT_OUT_TOPICS = {"bumper-ignore", "no-bumper"}


def project_page(homepage: str) -> str:
    m = PROJECT_PAGE.match((homepage or "").strip())
    return f"https://owasp.org/projects/{m.group(1).lower()}" if m else ""


def repo_kind(name: str, page: str) -> str:
    """site: an owasp.org project website repo (www-project-*); project: a repo whose homepage is
    its owasp.org project page; chapter: a chapter website repo; other: everything else."""
    lower = name.lower()
    if lower.startswith("www-project-"):
        return "site"
    if lower.startswith("www-chapter-"):
        return "chapter"
    return "project" if page else "other"


def repo_record(repo: Dict) -> Dict:
    """The fields the page uses, with empty values left out to keep the file small."""
    index_md = repo.get("index_md") or {}
    last_commit = repo.get("last_commit") or {}
    name = repo.get("name", "")
    page = project_page(repo.get("homepage", ""))
    topics = repo.get("topics") or []
    record = {
        "name": name,
        "description": repo.get("description") or "",
        "url": repo.get("html_url", ""),
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "issues": repo.get("open_issues_count", 0),
        "prs": repo.get("open_prs_count", 0),
        "created": repo.get("created_at", ""),
        "updated": repo.get("updated_at", ""),
        "pushed": repo.get("pushed_at", ""),
        "human": repo.get("human_at", ""),
        "bot_only": bool(repo.get("bot_only")),
        "language": repo.get("language") or "",
        "topics": topics,
        "archived": bool(repo.get("archived")),
        "issues_off": repo.get("has_issues") is False,
        "fork": bool(repo.get("fork")),
        "template": bool(repo.get("is_template")),
        "empty": repo.get("size") == 0,
        "reminder": repo.get("open_reminder") or {},
        "kind": repo_kind(name, page),
        "project_page": page,
        "opted_out": bool(OPT_OUT_TOPICS & {t.lower() for t in topics}),
        "commit": {k: last_commit.get(k, "") for k in ("message", "author", "author_url", "date")} if last_commit else {},
        "title": index_md.get("title", ""),
        "pitch": index_md.get("pitch", ""),
        "tags": index_md.get("tags") or [],
        "level": index_md.get("level"),
        "region": index_md.get("region", ""),
        "country": index_md.get("country", ""),
    }
    return {k: v for k, v in record.items() if v not in ("", [], {}, None, 0) or k in ("name", "archived", "kind")}


def build_data(repos: List[Dict], org: str) -> Dict:
    return {
        "org": org,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(repos),
        "repos": [repo_record(r) for r in repos],
    }


def main():
    org = os.environ.get('GITHUB_ORG', 'owasp')
    token = os.environ.get('GITHUB_TOKEN', '')
    output_file = os.environ.get('OUTPUT_FILE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public', 'data', 'repos.json'))
    started = time.time()

    print(f"Fetching repositories for organization: {org} ({'GraphQL' if token else 'REST, no token: no PR counts, last commit or index.md'})")
    repos = fetch_repos_graphql(org, token) if token else fetch_repos(org)
    print(f"Found {len(repos)} repositories")
    reminders = fetch_reminders(org, token)
    print(f"Found reminder issues on {len(reminders)} repositories ({sum(r['state'] == 'open' for r in reminders.values())} open)")
    for repo in repos:
        repo["open_reminder"] = reminders.get(repo.get("name", ""))

    data = build_data(repos, org)
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(repos)} repositories to {output_file} in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
