#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone

SOURCE = os.getenv("MAIN_DATA_SOURCE", "github_data.json")
OUT = os.getenv("MAIN_DATA_OUT", "main_data.json")
MIGRATION_PROGRESS = {
    "BLT-Next": 100,
    "BLT-University": 95,
    "BLT-Waypoint": 90,
    "owasp-blt.github.io": 90,
}
MIGRATION_SUMMARY_REPOS = ("owasp-blt.github.io", "BLT-Next", "BLT-University")
TOTAL_REPOS = 55


def migration_summary():
    migrated_repos = [
        name for name in MIGRATION_SUMMARY_REPOS
        if MIGRATION_PROGRESS.get(name, 0) > 0
    ]
    completion_points = sum(MIGRATION_PROGRESS.get(name, 0) for name in MIGRATION_SUMMARY_REPOS)
    return {
        "migrated_repos": len(migrated_repos),
        "total_repos": TOTAL_REPOS,
        "percent": round(completion_points / TOTAL_REPOS, 1),
    }


def main():
    with open(SOURCE, "r", encoding="utf-8") as f:
        github = json.load(f)

    repos = []
    for repo in github.get("repos", []):
        repos.append({
            "id": repo.get("id"),
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "html_url": repo.get("html_url"),
            "description": repo.get("description"),
            "homepage": repo.get("homepage"),
            "topics": repo.get("topics", []),
            "language": repo.get("language"),
            "fork": repo.get("fork", False),
            "archived": repo.get("archived", False),
            "updated_at": repo.get("updated_at"),
            "gitlab_migration_progress": MIGRATION_PROGRESS.get(repo.get("name"), 0),
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "main",
        "org": github.get("org", "OWASP-BLT"),
        "migration": migration_summary(),
        "repos": repos,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
        f.write("\n")


if __name__ == "__main__":
    main()
