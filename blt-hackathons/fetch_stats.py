#!/usr/bin/env python3
"""
Fetch GitHub stats for all hackathons and save to hackathon-data/ directory.
This script is run every hour via GitHub Actions to keep data fresh.

The frontend simply loads the resulting JSON files without making any live
GitHub API calls.

OPTIMIZATIONS:
- Skip ended hackathons (keeps historical data static)
- Incremental updates (only fetch PRs/reviews updated since last run)
- Org repos caching (fetch once, reuse for all hackathons)
- Early exit on sorted queries (stops when no more relevant data)
"""

import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


def is_hackathon_active(start_time, end_time):
    """Check if a hackathon is currently active or upcoming."""
    now = datetime.now(timezone.utc)
    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    # Keep updating if hackathon hasn't ended yet
    return now <= end_dt


def load_existing_data(slug):
    """Load existing hackathon data if it exists."""
    output_path = f"hackathon-data/{slug}.json"
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Could not load existing data for %s: %s", slug, exc)
    return None


def make_request(url, token=None, retry_count=3):
    """Make a single GitHub API request with retry/back-off logic."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "BLT-Hackathons-Stats-Fetcher/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for attempt in range(retry_count):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            if e.code in (429, 403):
                reset = e.headers.get("X-RateLimit-Reset")
                wait = max(int(reset) - int(time.time()) + 5, 10) if reset else 60
                logger.warning("Rate limited on %s. Waiting %ds...", url, min(wait, 300))
                time.sleep(min(wait, 300))
            elif e.code == 404:
                logger.warning("Not found: %s", url)
                return None
            else:
                logger.error("HTTP %d for %s: %s", e.code, url, e.reason)
                if attempt < retry_count - 1:
                    time.sleep(5 * (attempt + 1))
                else:
                    return None
        except URLError as e:
            logger.error("URL error for %s: %s", url, e)
            if attempt < retry_count - 1:
                time.sleep(5 * (attempt + 1))
            else:
                return None
    return None


def fetch_all_pages(base_url, token=None):
    """Fetch all pages from a paginated GitHub API endpoint."""
    all_items = []
    page = 1
    per_page = 100

    while True:
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}per_page={per_page}&page={page}"
        items = make_request(url, token)

        if not items:
            break

        all_items.extend(items)

        if len(items) < per_page:
            break

        page += 1
        time.sleep(0.2)  # Be gentle with the API

    logger.info("Fetched %d items from %s", len(all_items), base_url.split("?")[0])
    return all_items


def fetch_org_repos(org, token=None):
    """Fetch all public repositories for a GitHub organization."""
    logger.info("Fetching repositories for organization: %s", org)
    url = f"{GITHUB_API_BASE}/orgs/{org}/repos?type=public"
    repos = fetch_all_pages(url, token)
    return [r["full_name"] for r in repos if r and "full_name" in r]


def fetch_pull_requests(owner, repo, start_dt, end_dt, token=None, since=None):
    """Fetch all pull requests for a repository within the date range.
    
    Args:
        since: Optional datetime to fetch only PRs updated since this time
    """
    logger.info("Fetching PRs for %s/%s%s", owner, repo, 
                f" (since {since.isoformat()})" if since else "")
    
    # Use updated sort for incremental fetching
    sort_param = "updated" if since else "created"
    url = (
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        f"/pulls?state=all&sort={sort_param}&direction=desc"
    )
    all_prs = fetch_all_pages(url, token)

    filtered = []
    for pr in all_prs:
        created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
        merged_at = (
            datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
            if pr.get("merged_at")
            else None
        )
        
        # If we have a since parameter, skip PRs not updated since then
        if since and updated_at < since:
            # Early exit: we're sorted by updated desc, so no more recent PRs
            break
            
        relevant_by_creation = start_dt <= created_at <= end_dt
        relevant_by_merge = merged_at and start_dt <= merged_at <= end_dt
        if relevant_by_creation or relevant_by_merge:
            pr["repository"] = f"{owner}/{repo}"
            filtered.append(pr)

    logger.info("  -> %d PRs in date range for %s/%s", len(filtered), owner, repo)
    return filtered


def fetch_reviews_for_pr(owner, repo, pr_number, token=None):
    """Fetch all reviews for a specific pull request (full pagination)."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    return fetch_all_pages(url, token)


def fetch_issues(owner, repo, start_dt, end_dt, token=None):
    """Fetch all issues (excluding PRs) for a repository within the date range."""
    logger.info("Fetching issues for %s/%s", owner, repo)
    url = (
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        "/issues?state=all&sort=created&direction=desc"
    )
    all_items = fetch_all_pages(url, token)

    filtered = []
    for item in all_items:
        if "pull_request" in item:
            continue  # GitHub returns PRs via the issues endpoint; skip them
        created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        closed_at = (
            datetime.fromisoformat(item["closed_at"].replace("Z", "+00:00"))
            if item.get("closed_at")
            else None
        )
        relevant_by_creation = start_dt <= created_at <= end_dt
        relevant_by_closure = closed_at and start_dt <= closed_at <= end_dt
        if relevant_by_creation or relevant_by_closure:
            item["repository"] = f"{owner}/{repo}"
            filtered.append(item)

    logger.info("  -> %d issues in date range for %s/%s", len(filtered), owner, repo)
    return filtered


def fetch_repo_metadata(owner, repo, token=None):
    """Fetch repository metadata (stars, forks, language, description)."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    data = make_request(url, token)
    if data:
        return {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "stargazers_count": data.get("stargazers_count", 0),
            "forks_count": data.get("forks_count", 0),
            "language": data.get("language"),
            "html_url": data.get("html_url"),
        }
    return None


def process_hackathon_stats(prs, all_reviews, issues, start_dt, end_dt, repositories):
    """Process fetched data and compute hackathon statistics."""
    # Build daily activity map for the full date range
    daily_activity = {}
    current_date = start_dt.date()
    end_date = end_dt.date()
    while current_date <= end_date:
        daily_activity[current_date.isoformat()] = {"total": 0, "merged": 0}
        current_date += timedelta(days=1)

    participants = {}
    repo_stats = {
        r: {"total": 0, "merged": 0, "issues": 0, "closedIssues": 0}
        for r in repositories
    }
    total_prs = 0
    merged_prs = 0
    # Pre-computed merged PR counts per day (used for the activity chart)
    daily_merged_prs = {}

    for pr in prs:
        is_merged = bool(pr.get("merged_at"))
        username = pr["user"]["login"]
        is_bot = "[bot]" in username or username.lower().endswith("bot")
        title = pr.get("title", "")
        is_copilot = "copilot" in username.lower() or "copilot" in title.lower()

        total_prs += 1
        if is_merged:
            merged_prs += 1

        # Track per-repository stats
        repo_key = pr.get("repository", "unknown")
        if repo_key not in repo_stats:
            repo_stats[repo_key] = {"total": 0, "merged": 0, "issues": 0, "closedIssues": 0}
        repo_stats[repo_key]["total"] += 1
        if is_merged:
            repo_stats[repo_key]["merged"] += 1

        # Track daily creation activity
        created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        created_date = created_at.date().isoformat()
        if created_date in daily_activity and start_dt <= created_at <= end_dt:
            daily_activity[created_date]["total"] += 1

        # Track daily merged activity
        if is_merged:
            merged_date = pr["merged_at"][:10]
            if merged_date in daily_activity:
                daily_activity[merged_date]["merged"] += 1
            daily_merged_prs[merged_date] = daily_merged_prs.get(merged_date, 0) + 1

        # Track participants (skip bots and Copilot)
        if not is_bot and not is_copilot:
            if username not in participants:
                participants[username] = {
                    "username": username,
                    "avatar": pr["user"].get("avatar_url", ""),
                    "url": pr["user"].get(
                        "html_url", f"https://github.com/{username}"
                    ),
                    "mergedCount": 0,
                    "prCount": 0,
                    "reviewCount": 0,
                    "reviews": [],
                }
            participants[username]["prCount"] += 1
            if is_merged:
                participants[username]["mergedCount"] += 1

    # Process reviews
    for review in all_reviews:
        username = review["user"]["login"]
        is_bot = "[bot]" in username or username.lower().endswith("bot")
        is_copilot = "copilot" in username.lower()
        state = review.get("state", "")

        if is_bot or is_copilot or state == "DISMISSED":
            continue

        submitted_at_str = review.get("submitted_at")
        if not submitted_at_str:
            continue

        submitted_at = datetime.fromisoformat(submitted_at_str.replace("Z", "+00:00"))
        if not (start_dt <= submitted_at <= end_dt):
            continue

        if username not in participants:
            participants[username] = {
                "username": username,
                "avatar": review["user"].get("avatar_url", ""),
                "url": review["user"].get(
                    "html_url", f"https://github.com/{username}"
                ),
                "mergedCount": 0,
                "prCount": 0,
                "reviewCount": 0,
                "reviews": [],
            }

        participants[username]["reviewCount"] += 1
        participants[username]["reviews"].append(
            {
                "id": review.get("id"),
                "state": review.get("state"),
                "submitted_at": review.get("submitted_at"),
                "html_url": review.get("html_url", ""),
                "pull_request_url": review.get(
                    "pull_request_url", review.get("html_url", "")
                ),
                "pull_request_title": review.get("pull_request_title", ""),
            }
        )

    # Process issues
    total_issues = 0
    closed_issues = 0
    for issue in issues:
        repo_key = issue.get("repository", "unknown")
        if repo_key not in repo_stats:
            repo_stats[repo_key] = {"total": 0, "merged": 0, "issues": 0, "closedIssues": 0}
        repo_stats[repo_key]["issues"] += 1
        total_issues += 1
        if issue["state"] == "closed":
            repo_stats[repo_key]["closedIssues"] += 1
            closed_issues += 1

    # Build sorted leaderboards
    leaderboard = sorted(
        [p for p in participants.values() if p["mergedCount"] > 0],
        key=lambda x: x["mergedCount"],
        reverse=True,
    )
    review_leaderboard = sorted(
        [p for p in participants.values() if p["reviewCount"] > 0],
        key=lambda x: x["reviewCount"],
        reverse=True,
    )

    return {
        "totalPRs": total_prs,
        "mergedPRs": merged_prs,
        "totalIssues": total_issues,
        "closedIssues": closed_issues,
        "participantCount": len(participants),
        "leaderboard": leaderboard,
        "reviewLeaderboard": review_leaderboard,
        "repoStats": repo_stats,
        "dailyActivity": daily_activity,
        "dailyMergedPRs": daily_merged_prs,
    }


def process_hackathon(hackathon_config, token, org_repos_cache=None):
    """Fetch all data for a single hackathon and return the processed stats.
    
    Args:
        org_repos_cache: Optional dict to cache org repos across hackathons
    """
    slug = hackathon_config["slug"]
    name = hackathon_config["name"]
    start_time = hackathon_config["startTime"]
    end_time = hackathon_config["endTime"]
    github_config = hackathon_config.get("github", {})
    organization = github_config.get("organization")
    explicit_repos = list(github_config.get("repositories", []))

    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    
    # Load existing data for incremental updates
    existing_data = load_existing_data(slug)
    since = None
    existing_pr_numbers = set()
    
    if existing_data:
        last_updated = existing_data.get("lastUpdated")
        if last_updated:
            # Fetch only data updated since last run (with 5 min buffer for safety)
            since = datetime.fromisoformat(last_updated.replace("Z", "+00:00")) - timedelta(minutes=5)
            logger.info("Incremental update for %s since %s", name, since.isoformat())
            
            # Track existing PRs to avoid re-fetching reviews
            if "stats" in existing_data:
                # Build set of PR numbers we already have
                # We'll need to reconstruct this from the stored data
                pass

    # Resolve repositories (explicit list + org repos)
    repositories = list(explicit_repos)
    if organization:
        # Use cached org repos if available
        if org_repos_cache and organization in org_repos_cache:
            org_repos = org_repos_cache[organization]
            logger.info("Using cached org repos for %s (%d repos)", organization, len(org_repos))
        else:
            try:
                org_repos = fetch_org_repos(organization, token)
                if org_repos and org_repos_cache is not None:
                    org_repos_cache[organization] = org_repos
            except Exception as exc:
                logger.error(
                    "Failed to fetch org repos for %s, using explicit list: %s",
                    organization,
                    exc,
                )
                org_repos = []
        
        if org_repos:
            combined = list({*repositories, *org_repos})
            repositories = combined
            logger.info(
                "Resolved %d repositories for %s (%d explicit + %d from org)",
                len(repositories),
                name,
                len(explicit_repos),
                len(org_repos),
            )

    if not repositories:
        logger.warning("No repositories found for hackathon: %s", name)
        return None

    # Fetch all PRs across all repositories (incremental if possible)
    all_prs = []
    new_or_updated_prs = []
    
    for repo_path in repositories:
        parts = repo_path.split("/")
        if len(parts) != 2:
            logger.warning("Skipping invalid repo path: %s", repo_path)
            continue
        owner, repo = parts
        try:
            prs = fetch_pull_requests(owner, repo, start_dt, end_dt, token, since=since)
            all_prs.extend(prs)
            if since:
                new_or_updated_prs.extend(prs)
        except Exception as exc:
            logger.error("Failed to fetch PRs for %s: %s", repo_path, exc)

    if since:
        logger.info("Total new/updated PRs fetched for %s: %d", name, len(new_or_updated_prs))
    else:
        logger.info("Total PRs fetched for %s: %d", name, len(all_prs))

    # Fetch reviews only for new/updated PRs (huge optimization!)
    all_reviews = []
    prs_to_fetch_reviews = new_or_updated_prs if since else all_prs
    
    if prs_to_fetch_reviews:
        logger.info("Fetching reviews for %d PRs", len(prs_to_fetch_reviews))
        for pr in prs_to_fetch_reviews:
            repo_path = pr.get("repository", "")
            parts = repo_path.split("/")
            if len(parts) != 2:
                continue
            owner, repo = parts
            pr_number = pr["number"]
            try:
                reviews = fetch_reviews_for_pr(owner, repo, pr_number, token)
                for review in reviews:
                    review["repository"] = repo_path
                    review["pull_request_url"] = pr.get("html_url", "")
                    review["pull_request_title"] = pr.get("title", "")
                all_reviews.extend(reviews)
            except Exception as exc:
                logger.error(
                    "Failed to fetch reviews for %s#%d: %s", repo_path, pr_number, exc
                )
    
        logger.info("Total reviews fetched for %s: %d", name, len(all_reviews))
    else:
        logger.info("No new PRs to fetch reviews for %s", name)

    # Fetch all issues across all repositories
    all_issues = []
    for repo_path in repositories:
        parts = repo_path.split("/")
        if len(parts) != 2:
            continue
        owner, repo = parts
        try:
            issues = fetch_issues(owner, repo, start_dt, end_dt, token)
            all_issues.extend(issues)
        except Exception as exc:
            logger.error("Failed to fetch issues for %s: %s", repo_path, exc)

    logger.info("Total issues fetched for %s: %d", name, len(all_issues))

    # Fetch repository metadata
    repo_data = []
    for repo_path in repositories:
        parts = repo_path.split("/")
        if len(parts) != 2:
            continue
        owner, repo = parts
        try:
            meta = fetch_repo_metadata(owner, repo, token)
            if meta:
                repo_data.append(meta)
        except Exception as exc:
            logger.error("Failed to fetch metadata for %s: %s", repo_path, exc)

    # Compute stats
    stats = process_hackathon_stats(
        all_prs, all_reviews, all_issues, start_dt, end_dt, repositories
    )
    stats["repoData"] = repo_data

    return {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "slug": slug,
        "name": name,
        "startTime": start_time,
        "endTime": end_time,
        "repositories": repositories,
        "stats": stats,
    }


def main():
    config_path = os.environ.get(
        "HACKATHONS_CONFIG_PATH", "/tmp/hackathons-config-parsed.json"
    )

    if not os.path.exists(config_path):
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        logger.warning(
            "No GITHUB_TOKEN set - API calls will be rate limited to 60/hr"
        )

    hackathons = config.get("hackathons", [])
    if not hackathons:
        logger.error("No hackathons found in config")
        sys.exit(1)

    # Create output directory
    os.makedirs("hackathon-data", exist_ok=True)
    
    # Cache for org repos to avoid fetching multiple times
    org_repos_cache = {}

    for hackathon in hackathons:
        slug = hackathon.get("slug", "unknown")
        name = hackathon.get("name", slug)
        start_time = hackathon.get("startTime")
        end_time = hackathon.get("endTime")
        
        # Skip ended hackathons (optimization!)
        if not is_hackathon_active(start_time, end_time):
            logger.info("⏭️  Skipping ended hackathon: %s (ended on %s)", name, end_time)
            # Verify the data file exists
            output_path = f"hackathon-data/{slug}.json"
            if not os.path.exists(output_path):
                logger.warning("⚠️  No data file found for ended hackathon %s, processing once", slug)
            else:
                continue
        
        logger.info("🔄 Processing active hackathon: %s", name)
        try:
            data = process_hackathon(hackathon, token, org_repos_cache)
            if data:
                output_path = f"hackathon-data/{slug}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                logger.info("✅ Saved stats for '%s' to %s", slug, output_path)
        except Exception as exc:
            logger.error("❌ Failed to process hackathon %s: %s", slug, exc)
            import traceback

            traceback.print_exc()

    # Update the top-level stats.json with basic summary info
    primary = hackathons[0] if hackathons else {}
    all_repos: set = set()
    for h in hackathons:
        for r in h.get("github", {}).get("repositories", []):
            all_repos.add(r)

    stats_data = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "repositories": len(all_repos),
        "hackathonName": primary.get("name", ""),
        "startTime": primary.get("startTime", ""),
        "endTime": primary.get("endTime", ""),
        "hackathons": [
            {
                "slug": h.get("slug", ""),
                "name": h.get("name", ""),
                "startTime": h.get("startTime", ""),
                "endTime": h.get("endTime", ""),
            }
            for h in hackathons
        ],
    }
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats_data, f, indent=2)
    logger.info("Updated stats.json")


if __name__ == "__main__":
    main()
