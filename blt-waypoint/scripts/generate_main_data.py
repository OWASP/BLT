#!/usr/bin/env python3
import csv
import json
import os

SOURCE = os.getenv("MAIN_DATA_SOURCE", "public/github_data.json")
OUT = os.getenv("MAIN_DATA_OUT", "public/main_data.csv")
JS_OUT = os.getenv("MAIN_DATA_JS_OUT", "public/main_data.js")
JSON_OUT = os.getenv("MAIN_DATA_JSON_OUT", "public/main_data.json")

GITLAB_URLS = {
    ".github": "https://git.owaspblt.org/BLT/dot_github",
    "BLT": "https://git.owaspblt.org/BLT/BLT-Core",
    "BLT-Action": "https://git.owaspblt.org/BLT/BLT-Action",
    "BLT-API": "https://git.owaspblt.org/BLT/BLT-API",
    "BLT-Byte": "https://git.owaspblt.org/BLT/BLT-Byte",
    "BLT-CLI": "https://git.owaspblt.org/BLT/BLT-CLI",
    "BLT-CVE": "https://git.owaspblt.org/BLT/BLT-CVE",
    "BLT-Dash": "https://git.owaspblt.org/BLT/BLT-Dash",
    "BLT-Design": "https://git.owaspblt.org/BLT/BLT-Design",
    "BLT-Design-Contest": "https://git.owaspblt.org/BLT/BLT-Design-Contest",
    "BLT-docs": "https://git.owaspblt.org/BLT/BLT-Docs",
    "BLT-Enforcement": "https://git.owaspblt.org/BLT/BLT-Enforcement",
    "BLT-Extension": "https://git.owaspblt.org/BLT/BLT-Extension",
    "BLT-Flutter": "https://git.owaspblt.org/BLT/BLT-Flutter",
    "BLT-Github-Sportscaster": "https://git.owaspblt.org/BLT/BLT-Gitcaster",
    "BLT-GSOC": "https://git.owaspblt.org/BLT/BLT-GSOC",
    "BLT-Hackathons": "https://git.owaspblt.org/BLT/BLT-Hackathons",
    "BLT-Ideas": "https://git.owaspblt.org/BLT/BLT-Ideas",
    "BLT-Jobs": "https://git.owaspblt.org/BLT/BLT-Jobs",
    "BLT-Ketchup": "https://git.owaspblt.org/BLT/BLT-Ketchup",
    "BLT-Leaf": "https://git.owaspblt.org/BLT/BLT-Leaf",
    "BLT-Lettuce": "https://git.owaspblt.org/BLT/BLT-Lettuce",
    "BLT-MCP": "https://git.owaspblt.org/BLT/BLT-MCP",
    "BLT-Monitor": "https://git.owaspblt.org/BLT/BLT-Monitor",
    "BLT-NetGuardian": "https://git.owaspblt.org/BLT/BLT-NetGuardian",
    "BLT-NetGuardian-Client": "https://git.owaspblt.org/BLT/BLT-NetGuardian-Client",
    "BLT-Newsletter": "https://git.owaspblt.org/BLT/BLT-Newsletter",
    "BLT-Next": "https://git.owaspblt.org/BLT/BLT-Next",
    "BLT-Nexus": "https://git.owaspblt.org/BLT/BLT-Nexus",
    "BLT-OSSH": "https://git.owaspblt.org/BLT/BLT-OSSH",
    "BLT-OWASP-Bumper": "https://git.owaspblt.org/BLT/BLT-OWASP-Bumper",
    "BLT-OWASP-metadata": "https://git.owaspblt.org/BLT/BLT-OWASP-Metadata",
    "BLT-OWASP-Projects": "https://git.owaspblt.org/BLT/BLT-OWASP-Projects",
    "BLT-OWASP-Wich": "https://git.owaspblt.org/BLT/BLT-OWASP-Wich",
    "BLT-Pages": "https://git.owaspblt.org/BLT/BLT-Pages",
    "BLT-Panini": "https://git.owaspblt.org/BLT/BLT-Panini",
    "BLT-Pool": "https://git.owaspblt.org/BLT/BLT-Pool",
    "BLT-Preflight": "https://git.owaspblt.org/BLT/BLT-Preflight",
    "BLT-Profiles": "https://git.owaspblt.org/BLT/BLT-Profiles",
    "BLT-Rewards": "https://git.owaspblt.org/BLT/BLT-Rewards",
    "BLT-SafeCloak": "https://git.owaspblt.org/BLT/BLT-SafeCloak",
    "BLT-Sammich": "https://git.owaspblt.org/BLT/BLT-Sammich",
    "BLT-Sizzle": "https://git.owaspblt.org/BLT/BLT-Sizzle",
    "BLT-Start": "https://git.owaspblt.org/BLT/BLT-Start",
    "BLT-Timer-Flutter": "https://git.owaspblt.org/BLT/BLT-Timer-Flutter",
    "BLT-Timer-Web": "https://git.owaspblt.org/BLT/BLT-Timer-Web",
    "BLT-Toasty": "https://git.owaspblt.org/BLT/BLT-Toasty",
    "BLT-Tomato": "https://git.owaspblt.org/BLT/BLT-Tomato",
    "BLT-University": "https://git.owaspblt.org/BLT/BLT-University",
    "BLT-Vanish": "https://git.owaspblt.org/BLT/BLT-Vanish",
    "BLT-Vanish-Web": "https://git.owaspblt.org/BLT/BLT-Vanish",
    "BLT-Vanish-Flutter": "https://git.owaspblt.org/BLT/BLT-Vanish-Flutter",
    "BLT-Zero": "https://git.owaspblt.org/BLT/BLT-Zero",
    "coderabbit": "https://git.owaspblt.org/BLT/coderabbit",
    "MY-GSOC-TOOL": "https://git.owaspblt.org/BLT/MY-GSOC-TOOL",
    "BLT-Waypoint": "https://git.owaspblt.org/BLT/BLT-Waypoint",
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
    for repo in github.get("repos", []):
        name = repo.get("name")
        gitlab_url = GITLAB_URLS.get(name, "")
        repos.append({
            "id": repo.get("id"),
            "name": name,
            "full_name": repo.get("full_name"),
            "html_url": repo.get("html_url"),
            "description": repo.get("description"),
            "homepage": repo.get("homepage"),
            "topics": repo.get("topics", []),
            "language": repo.get("language"),
            "fork": repo.get("fork", False),
            "archived": repo.get("archived", False),
            "updated_at": repo.get("updated_at"),
            "gitlab_migration_progress": 100 if gitlab_url else 0,
            "gitlab_url": gitlab_url,
        })

    if not repos:
        raise RuntimeError(f"{SOURCE} did not contain repositories; keeping the existing main data files")

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for repo in repos:
            writer.writerow({
                **repo,
                "topics": "|".join(repo["topics"]),
            })

    with open(OUT, "r", encoding="utf-8") as f:
        csv_text = f.read()

    with open(JS_OUT, "w", encoding="utf-8") as f:
        f.write("window.BLT_MAIN_DATA_CSV = ")
        json.dump(csv_text, f)
        f.write(";\n")

    migrated_repos = sum(1 for repo in repos if repo["gitlab_migration_progress"] == 100)
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": github.get("generated_at"),
            "source": "main",
            "org": github.get("org"),
            "migration": {
                "migrated_repos": migrated_repos,
                "total_repos": len(repos),
                "percent": round(migrated_repos / len(repos) * 100, 1) if repos else 0,
            },
            "repos": repos,
        }, f, separators=(",", ":"))
        f.write("\n")


if __name__ == "__main__":
    main()
