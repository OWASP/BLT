#!/usr/bin/env python3
import csv
import json
import os

SOURCE = os.getenv("MAIN_DATA_SOURCE", "public/github_data.json")
OUT = os.getenv("MAIN_DATA_OUT", "public/main_data.csv")
JS_OUT = os.getenv("MAIN_DATA_JS_OUT", "public/main_data.js")
JSON_OUT = os.getenv("MAIN_DATA_JSON_OUT", "public/main_data.json")

GITLAB_URLS = {
    ".github": "https://git.owaspblt.org/BLT/BLT/tree/main/dot_github",
    "BLT": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-core",
    "BLT-Action": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-action",
    "BLT-API": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-api",
    "BLT-Byte": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-byte",
    "BLT-CLI": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-cli",
    "BLT-CVE": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-cve",
    "BLT-Dash": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-dash",
    "BLT-Design": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-design",
    "BLT-Design-Contest": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-design-contest",
    "BLT-docs": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-docs",
    "BLT-Enforcement": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-enforcement",
    "BLT-Extension": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-extension",
    "BLT-Flutter": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-flutter",
    "BLT-Github-Sportscaster": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-gitcaster",
    "BLT-GSOC": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-gsoc",
    "BLT-Hackathons": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-hackathons",
    "BLT-Ideas": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-ideas",
    "BLT-Jobs": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-jobs",
    "BLT-Ketchup": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-ketchup",
    "BLT-Leaf": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-leaf",
    "BLT-Lettuce": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-lettuce",
    "BLT-MCP": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-mcp",
    "BLT-Monitor": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-monitor",
    "BLT-NetGuardian": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-netguardian",
    "BLT-NetGuardian-Client": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-netguardian-client",
    "BLT-Newsletter": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-newsletter",
    "BLT-Next": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-next",
    "BLT-Nexus": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-nexus",
    "BLT-OSSH": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-ossh",
    "BLT-OWASP-Bumper": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-bumper",
    "BLT-OWASP-metadata": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-metadata",
    "BLT-OWASP-Projects": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-projects",
    "BLT-OWASP-Wich": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-wich",
    "BLT-Pages": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-pages",
    "BLT-Panini": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-panini",
    "BLT-Pool": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-pool",
    "BLT-Preflight": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-preflight",
    "BLT-Profiles": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-profiles",
    "BLT-Rewards": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-rewards",
    "BLT-SafeCloak": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-safecloak",
    "BLT-Sammich": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-sammich",
    "BLT-Sizzle": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-sizzle",
    "BLT-Start": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-start",
    "BLT-Timer-Flutter": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-timer-flutter",
    "BLT-Timer-Web": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-timer-web",
    "BLT-Toasty": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-toasty",
    "BLT-Tomato": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-tomato",
    "BLT-University": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-university",
    "BLT-Vanish": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-vanish",
    "BLT-Vanish-Web": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-vanish",
    "BLT-Vanish-Flutter": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-vanish-flutter",
    "BLT-Zero": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-zero",
    "coderabbit": "https://git.owaspblt.org/BLT/BLT/tree/main/coderabbit",
    "MY-GSOC-TOOL": "https://git.owaspblt.org/BLT/BLT/tree/main/my-gsoc-tool",
    "BLT-Waypoint": "https://git.owaspblt.org/BLT/BLT/tree/main/blt-waypoint",
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
