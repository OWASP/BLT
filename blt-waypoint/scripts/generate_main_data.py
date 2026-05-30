#!/usr/bin/env python3
import csv
import json
import os

SOURCE = os.getenv("MAIN_DATA_SOURCE", "github_data.json")
OUT = os.getenv("MAIN_DATA_OUT", "main_data.csv")
JS_OUT = os.getenv("MAIN_DATA_JS_OUT", "main_data.js")
JSON_OUT = os.getenv("MAIN_DATA_JSON_OUT", "main_data.json")
GITLAB_URLS = {
    ".github": "https://gitlab.com/owasp-blt/dot_github",
    "BLT": "https://gitlab.com/owasp-blt/blt",
    "BLT-Action": "https://gitlab.com/owasp-blt/blt-action",
    "BLT-API": "https://gitlab.com/owasp-blt/blt-api",
    "BLT-Byte": "https://gitlab.com/owasp-blt/blt-byte",
    "BLT-CLI": "https://gitlab.com/owasp-blt/blt-cli",
    "BLT-CVE": "https://gitlab.com/owasp-blt/blt-cve",
    "BLT-Dash": "https://gitlab.com/owasp-blt/blt-dash",
    "BLT-Design": "https://gitlab.com/owasp-blt/blt-design",
    "BLT-Design-Contest": "https://gitlab.com/owasp-blt/blt-design-contest",
    "BLT-docs": "https://gitlab.com/owasp-blt/blt-docs",
    "BLT-Enforcement": "https://gitlab.com/owasp-blt/blt-enforcement",
    "BLT-Extension": "https://gitlab.com/owasp-blt/blt-extension",
    "BLT-Flutter": "https://gitlab.com/owasp-blt/blt-flutter",
    "BLT-Github-Sportscaster": "https://gitlab.com/owasp-blt/blt-gitcaster",
    "BLT-GSOC": "https://gitlab.com/owasp-blt/blt-gsoc",
    "BLT-Hackathons": "https://gitlab.com/owasp-blt/blt-hackathons",
    "BLT-Ideas": "https://gitlab.com/owasp-blt/blt-ideas",
    "BLT-Jobs": "https://gitlab.com/owasp-blt/blt-jobs",
    "BLT-Ketchup": "https://gitlab.com/owasp-blt/blt-ketchup",
    "BLT-Leaf": "https://gitlab.com/owasp-blt/blt-leaf",
    "BLT-Lettuce": "https://gitlab.com/owasp-blt/blt-lettuce",
    "BLT-MCP": "https://gitlab.com/owasp-blt/blt-mcp",
    "BLT-Monitor": "https://gitlab.com/owasp-blt/blt-monitor",
    "BLT-NetGuardian": "https://gitlab.com/owasp-blt/blt-netguardian",
    "BLT-NetGuardian-Client": "https://gitlab.com/owasp-blt/blt-netguardian-client",
    "BLT-Newsletter": "https://gitlab.com/owasp-blt/blt-newsletter",
    "BLT-Next": "https://gitlab.com/owasp-blt/blt-next",
    "BLT-Nexus": "https://gitlab.com/owasp-blt/blt-nexus",
    "BLT-OSSH": "https://gitlab.com/owasp-blt/blt-ossh",
    "BLT-OWASP-Bumper": "https://gitlab.com/owasp-blt/blt-owasp-bumper",
    "BLT-OWASP-metadata": "https://gitlab.com/owasp-blt/blt-owasp-metadata",
    "BLT-OWASP-Projects": "https://gitlab.com/owasp-blt/blt-owasp-projects",
    "BLT-OWASP-Wich": "https://gitlab.com/owasp-blt/blt-owasp-wich",
    "BLT-Pages": "https://gitlab.com/owasp-blt/blt-pages",
    "BLT-Panini": "https://gitlab.com/owasp-blt/blt-panini",
    "BLT-Pool": "https://gitlab.com/owasp-blt/blt-pool",
    "BLT-Preflight": "https://gitlab.com/owasp-blt/blt-preflight",
    "BLT-Profiles": "https://gitlab.com/owasp-blt/blt-profiles",
    "BLT-Rewards": "https://gitlab.com/owasp-blt/blt-rewards",
    "BLT-SafeCloak": "https://gitlab.com/owasp-blt/blt-safecloak",
    "BLT-Sammich": "https://gitlab.com/owasp-blt/blt-sammich",
    "BLT-Sizzle": "https://gitlab.com/owasp-blt/blt-sizzle",
    "BLT-Start": "https://gitlab.com/owasp-blt/blt-start",
    "BLT-Timer-Flutter": "https://gitlab.com/owasp-blt/blt-timer-flutter",
    "BLT-Timer-Web": "https://gitlab.com/owasp-blt/blt-timer-web",
    "BLT-Toasty": "https://gitlab.com/owasp-blt/blt-toasty",
    "BLT-Tomato": "https://gitlab.com/owasp-blt/blt-tomato",
    "BLT-University": "https://gitlab.com/owasp-blt/blt-university",
    "BLT-Vanish": "https://gitlab.com/owasp-blt/blt-vanish",
    "BLT-Vanish-Web": "https://gitlab.com/owasp-blt/blt-vanish",
    "BLT-Vanish-Flutter": "https://gitlab.com/owasp-blt/blt-vanish-flutter",
    "BLT-Zero": "https://gitlab.com/owasp-blt/blt-zero",
    "coderabbit": "https://gitlab.com/owasp-blt/coderabbit",
    "MY-GSOC-TOOL": "https://gitlab.com/owasp-blt/my-gsoc-tool",
    "owasp-blt.github.io": "https://gitlab.com/owasp-blt/blt-waypoint",
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
