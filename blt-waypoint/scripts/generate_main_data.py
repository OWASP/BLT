#!/usr/bin/env python3
"""The Main tab data (main_data.csv/.js/.json) from the archived GitHub record, with forge URLs.

Every project is a folder of https://git.owaspblt.org/BLT; html_url is the folder URL. The output
depends only on public/github_data.json and scripts/routing/projects.tsv, so the files are
committed (tests/test_forge_data.py checks they are current), not refreshed on a schedule.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forge_urls  # noqa: E402

SOURCE = os.getenv("MAIN_DATA_SOURCE", "public/github_data.json")
OUT = os.getenv("MAIN_DATA_OUT", "public/main_data.csv")
JS_OUT = os.getenv("MAIN_DATA_JS_OUT", "public/main_data.js")
JSON_OUT = os.getenv("MAIN_DATA_JSON_OUT", "public/main_data.json")

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
    "folder",
)


def main():
    with open(SOURCE, "r", encoding="utf-8") as f:
        github = json.load(f)

    index = forge_urls.folder_index()
    repos = []
    for repo in github.get("repos", []):
        name = repo.get("name")
        folder = forge_urls.resolve(name, index) or ""
        html_url = forge_urls.folder_url(folder) if folder else forge_urls.rewrite_text(repo.get("html_url") or "", index)
        repos.append({
            "id": repo.get("id"),
            "name": name,
            "full_name": repo.get("full_name"),
            "html_url": html_url,
            "description": repo.get("description"),
            "homepage": repo.get("homepage"),
            "topics": repo.get("topics", []),
            "language": repo.get("language"),
            "fork": repo.get("fork", False),
            "archived": repo.get("archived", False),
            "updated_at": repo.get("updated_at"),
            "folder": folder,
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

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": github.get("generated_at"),
            "source": "main",
            "org": github.get("org"),
            "forge_url": forge_urls.WEB_URL,
            "repos": repos,
        }, f, separators=(",", ":"))
        f.write("\n")


if __name__ == "__main__":
    main()
