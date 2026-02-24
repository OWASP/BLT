#!/usr/bin/env python3
"""
Fetch all OWASP-BLT org repos from the GitHub REST API and write data.json.

Environment variables:
  GH_TOKEN  – GitHub personal access token or GITHUB_TOKEN (optional but
               strongly recommended to avoid the 60 req/hr unauthenticated limit)
  ORG       – GitHub organisation name (default: OWASP-BLT)
  OUT_FILE  – output path (default: data.json)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

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
            return json.loads(resp.read().decode())
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


def fetch_languages(repo_full_name: str) -> dict:
    """Return the language breakdown (bytes) for a single repo."""
    try:
        return make_request(f"{API_BASE}/repos/{repo_full_name}/languages")
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"  Warning: could not fetch languages for {repo_full_name}: {exc}", file=sys.stderr)
        return {}


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
    total_watchers = sum(r.get("watchers_count", 0) for r in repos)

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
        "watchers_count", "fork", "archived", "private", "topics",
        "default_branch", "updated_at", "created_at", "pushed_at",
        "license", "visibility",
    }
    slim_repos = [
        {k: v for k, v in repo.items() if k in KEEP_FIELDS}
        for repo in repos
    ]

    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "org": ORG,
        "cumulative": {
            "total_repos":      len(repos),
            "total_stars":      total_stars,
            "total_forks":      total_forks,
            "total_open_issues": total_issues,
            "total_watchers":   total_watchers,
            "lang_bytes":       dict(
                sorted(all_lang_bytes.items(), key=lambda x: x[1], reverse=True)
            ),
            "lang_repo_count":  dict(
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
