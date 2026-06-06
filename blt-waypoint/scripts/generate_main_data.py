#!/usr/bin/env python3
import csv
import json
import os
from datetime import datetime, timezone

SOURCE = os.getenv("MAIN_DATA_SOURCE", "public/github_data.json")
OUT = os.getenv("MAIN_DATA_OUT", "public/main_data.csv")
JS_OUT = os.getenv("MAIN_DATA_JS_OUT", "public/main_data.js")
JSON_OUT = os.getenv("MAIN_DATA_JSON_OUT", "public/main_data.json")
MIGRATION_PROGRESS = {
    "BLT-Next": 100,
    "BLT-API": 100,
    "BLT-University": 95,
    "BLT-GSOC": 90,
    "owasp-blt.github.io": 90,
}
GITLAB_URLS = {
    "owasp-blt.github.io": "https://gitlab.com/owasp-blt/blt-waypoint",
    "BLT-GSOC": "https://gitlab.com/owasp-blt/blt-gsoc",
    "BLT-University": "https://gitlab.com/owasp-blt/blt-university",
    "BLT-Next": "https://gitlab.com/owasp-blt/BLT-Next",
    "BLT-API": "https://gitlab.com/owasp-blt/blt-api",
}
FIELDS = (
    "id",
    "name",
    "full_name",
    "html_url",
    "description",
    "homepage",
    "topics",
    "language",
    "fork",
    "archived",
    "updated_at",
    "gitlab_migration_progress",
    "gitlab_url",
)


def main():
    with open(SOURCE, "r", encoding="utf-8") as f:
        github = json.load(f)

    repos = []
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for repo in github.get("repos", []):
            name = repo.get("name")
            row = {
                "id": repo.get("id"),
                "name": name,
                "full_name": repo.get("full_name"),
                "html_url": repo.get("html_url"),
                "description": repo.get("description"),
                "homepage": repo.get("homepage"),
                "topics": "|".join(repo.get("topics", [])),
                "language": repo.get("language"),
                "fork": repo.get("fork", False),
                "archived": repo.get("archived", False),
                "updated_at": repo.get("updated_at"),
                "gitlab_migration_progress": MIGRATION_PROGRESS.get(name, 0),
                "gitlab_url": GITLAB_URLS.get(name, ""),
            }
            writer.writerow(row)
            repos.append({
                **row,
                "topics": repo.get("topics", []),
            })

    with open(OUT, "r", encoding="utf-8") as f:
        csv_text = f.read()

    with open(JS_OUT, "w", encoding="utf-8") as f:
        f.write("window.BLT_MAIN_DATA_CSV = ")
        json.dump(csv_text, f)
        f.write(";\n")

    total_repos = len(repos)
    completion_points = sum(repo["gitlab_migration_progress"] for repo in repos)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "main",
        "org": github.get("org", "OWASP-BLT"),
        "migration": {
            "migrated_repos": sum(1 for repo in repos if repo["gitlab_migration_progress"] > 0),
            "total_repos": total_repos,
            "percent": round(completion_points / total_repos, 1) if total_repos else 0,
        },
        "repos": repos,
    }

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
        f.write("\n")


if __name__ == "__main__":
    main()
