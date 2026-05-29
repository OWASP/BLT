#!/usr/bin/env python3
import csv
import json
import os

SOURCE = os.getenv("MAIN_DATA_SOURCE", "github_data.json")
OUT = os.getenv("MAIN_DATA_OUT", "main_data.csv")
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

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for repo in github.get("repos", []):
            name = repo.get("name")
            writer.writerow({
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
            })


if __name__ == "__main__":
    main()
