#!/usr/bin/env python3
"""
Fetch every repository in the OWASP GitHub organization and write the data the Bumper page
(public/index.html) shows: public/data/repos.json. Standard library only.

    GITHUB_TOKEN=... python3 generate_repo_list.py        # full data (~4 requests per repo)
    python3 generate_repo_list.py                         # repo list only (no token needed)

Environment: GITHUB_ORG (owasp), OUTPUT_FILE (public/data/repos.json), FETCH_SPARKLINES,
FETCH_METADATA (true), MAX_WORKERS (20).
"""

import base64
import concurrent.futures
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
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


def fetch_index_md(owner: str, repo: str, token: str = None) -> Optional[Dict]:
    """Fetch and parse index.md from a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/index.md"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OWASP-Bumper-Repo-List-Generator"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            content_b64 = data.get("content", "")
            if content_b64:
                content = base64.b64decode(content_b64).decode('utf-8', errors='replace')
                return parse_yaml_frontmatter(content)
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None
    
    return None


def fetch_open_prs_count(owner: str, repo: str, token: str = None) -> int:
    """Fetch the count of open pull requests for a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=1"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OWASP-Bumper-Repo-List-Generator"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            # Check the Link header for total count
            link_header = response.getheader('Link', '')
            if 'rel="last"' in link_header:
                # Extract the page number from the last link
                match = re.search(r'page=(\d+)>; rel="last"', link_header)
                if match:
                    return int(match.group(1))
            # If no Link header, count the items returned
            data = json.loads(response.read().decode())
            return len(data)
    except urllib.error.HTTPError:
        return 0
    except Exception:
        return 0


def fetch_last_commit(owner: str, repo: str, token: str = None) -> Optional[Dict]:
    """Fetch the most recent commit for a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OWASP-Bumper-Repo-List-Generator"
    }

    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data:
                commit = data[0]
                author_obj = commit.get("author") or {}
                git_author = commit.get("commit", {}).get("author") or {}
                message = commit.get("commit", {}).get("message", "") or ""
                # Use only the first line of the commit message
                message = message.split("\n")[0].strip()
                return {
                    "message": message,
                    "author": author_obj.get("login") or git_author.get("name", ""),
                    "avatar_url": author_obj.get("avatar_url", ""),
                    "author_url": author_obj.get("html_url", ""),
                    "date": git_author.get("date", ""),
                }
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None

    return None


def fetch_participation_stats(owner: str, repo: str, token: str = None) -> Optional[List[int]]:
    """Fetch weekly commit participation stats for a repository (last 52 weeks)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/stats/participation"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OWASP-Bumper-Repo-List-Generator"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 202:
                # Stats are being computed, return None
                return None
            data = json.loads(response.read().decode())
            # Return the 'all' array which contains commit counts for all contributors
            return data.get("all", [])
    except urllib.error.HTTPError as e:
        if e.code == 202:
            # Stats are being computed
            return None
        return None
    except Exception:
        return None


def fetch_repos(org: str, token: str = None) -> List[Dict]:
    """Fetch all repositories for a GitHub organization."""
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

def repo_record(repo: Dict) -> Dict:
    """The fields the page uses, with empty values left out to keep the file small."""
    index_md = repo.get("index_md") or {}
    last_commit = repo.get("last_commit") or {}
    name = repo.get("name", "")
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
        "language": repo.get("language") or "",
        "topics": repo.get("topics") or [],
        "archived": bool(repo.get("archived")),
        "issues_off": repo.get("has_issues") is False,
        "kind": "project" if "www-project" in name.lower() else "chapter" if "www-chapter" in name.lower() else "other",
        "sparkline": repo.get("sparkline") or [],
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


def _fetch_repo_extra_data(repo: Dict, org: str, token: str, fetch_sparklines: bool, fetch_metadata: bool) -> Dict:
    """Fetch all extra data for a single repository (sparkline + metadata).

    Modifies *repo* in-place and also returns it, so it can be used both as a
    concurrent.futures worker target and for direct calls.

    Parameters:
        repo: Repository dict from the GitHub API (modified in place).
        org: GitHub organisation name, used as fallback owner.
        token: GitHub API token; pass empty string to skip authenticated calls.
        fetch_sparklines: Whether to fetch 52-week participation stats.
        fetch_metadata: Whether to fetch index.md, PR count, and last commit.

    Returns:
        The same *repo* dict with sparkline/index_md/open_prs_count/last_commit set.
    """
    owner = repo.get("owner", {}).get("login", org)
    repo_name = repo.get("name", "")

    if not repo_name:
        repo["sparkline"] = []
        repo["index_md"] = {}
        repo["open_prs_count"] = 0
        repo["last_commit"] = {}
        return repo

    if fetch_sparklines and token:
        sparkline_data = fetch_participation_stats(owner, repo_name, token)
        repo["sparkline"] = sparkline_data if sparkline_data else []
    else:
        repo["sparkline"] = []

    if fetch_metadata and token:
        repo["index_md"] = fetch_index_md(owner, repo_name, token) or {}
        repo["open_prs_count"] = fetch_open_prs_count(owner, repo_name, token)
        repo["last_commit"] = fetch_last_commit(owner, repo_name, token) or {}
    else:
        repo["index_md"] = {}
        repo["open_prs_count"] = 0
        repo["last_commit"] = {}

    return repo


def main():
    org = os.environ.get('GITHUB_ORG', 'owasp')
    token = os.environ.get('GITHUB_TOKEN', '')
    output_file = os.environ.get('OUTPUT_FILE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public', 'data', 'repos.json'))
    fetch_sparklines = os.environ.get('FETCH_SPARKLINES', 'true').lower() == 'true'
    fetch_metadata = os.environ.get('FETCH_METADATA', 'true').lower() == 'true'
    max_workers = 20
    try:
        max_workers = int(os.environ.get('MAX_WORKERS', '20'))
    except ValueError:
        print("Warning: MAX_WORKERS is not a valid integer, defaulting to 20", file=sys.stderr)

    print(f"Fetching repositories for organization: {org}")
    repos = fetch_repos(org, token)
    print(f"Found {len(repos)} repositories")

    if (fetch_sparklines and token) or (fetch_metadata and token):
        print(f"Fetching extra data for {len(repos)} repositories using {max_workers} parallel workers...")
        completed = 0
        total = len(repos)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _fetch_repo_extra_data, repo, org, token, fetch_sparklines, fetch_metadata
                ): repo
                for repo in repos
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()  # re-raises any exception; repo dict is modified in place
                except Exception as exc:
                    failed_repo = futures[future]
                    print(f"  Warning: failed to fetch extra data for {failed_repo.get('name', '?')}: {exc}", file=sys.stderr)
                completed += 1
                if completed % 100 == 0 or completed == total:
                    print(f"  Completed {completed}/{total}")

        print(f"  Done fetching extra data for {total} repositories")
    else:
        print("Skipping extra data fetch (no token or both FETCH_SPARKLINES and FETCH_METADATA are false)")
        for repo in repos:
            repo["sparkline"] = []
            repo["index_md"] = {}
            repo["open_prs_count"] = 0
            repo["last_commit"] = {}

    data = build_data(repos, org)

    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(repos)} repositories to {output_file}")

if __name__ == "__main__":
    main()
