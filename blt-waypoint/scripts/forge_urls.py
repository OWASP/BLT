#!/usr/bin/env python3
"""Project folders of the monorepo and their git.owaspblt.org URLs.

gitlab.com/owasp-blt is closed; every BLT project is a folder of https://git.owaspblt.org/BLT.
``python scripts/forge_urls.py data/github_archive.json`` rewrites the gitlab.com/owasp-blt
project URLs in that file to forge folder URLs (idempotent).
"""

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FORGE = "https://git.owaspblt.org"
WEB_URL = f"{FORGE}/BLT"
GITLAB_PROJECT = re.compile(r"https?://gitlab\.com/owasp-blt/([A-Za-z0-9_.-]+)(?:/[^\s\"')<>]*)?")


def projects(root=ROOT):
    """[(folder, display name, [aliases])] from scripts/routing/projects.tsv (retired names skipped)."""
    rows = []
    with open(os.path.join(root, "scripts", "routing", "projects.tsv"), encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t") + ["", ""]
            if parts[0] and parts[0] != "-":
                aliases = [a.strip() for a in parts[2].split(",") if a.strip()]
                rows.append((parts[0], parts[1] or parts[0], aliases))
    return rows


def folder_index(root=ROOT):
    """Lower-cased folder, display name and alias -> folder."""
    index = {}
    for folder, name, aliases in projects(root):
        for key in [folder, name] + aliases:
            index.setdefault(key.lower(), folder)
    return index


def folder_url(folder):
    return f"{WEB_URL}/tree/main/{folder}"


def resolve(name, index):
    """The folder for a project, GitHub repository or gitlab.com slug name, else None."""
    return index.get(str(name or "").strip().lower())


def rewrite_text(text, index):
    """Replace gitlab.com/owasp-blt/<slug>[/...] URLs with the folder URL (or the repo URL)."""
    def replace(match):
        folder = resolve(match.group(1), index)
        return folder_url(folder) if folder else WEB_URL
    return GITLAB_PROJECT.sub(replace, text)


def rewrite_value(value, index):
    if isinstance(value, str):
        return rewrite_text(value, index)
    if isinstance(value, list):
        return [rewrite_value(v, index) for v in value]
    if isinstance(value, dict):
        return {k: rewrite_value(v, index) for k, v in value.items()}
    return value


def rewrite_json_file(path, index=None):
    """Rewrite a JSON file in place; returns True when it changed."""
    index = index or folder_index()
    with open(path, encoding="utf-8") as handle:
        original = handle.read()
    data = json.loads(original)
    updated = rewrite_value(data, index)
    if updated == data:
        return False
    compact = "\n" not in original.strip()
    with open(path, "w", encoding="utf-8") as handle:
        if compact:
            json.dump(updated, handle, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(updated, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return True


if __name__ == "__main__":
    for target in sys.argv[1:]:
        print(f"{target}: {'rewritten' if rewrite_json_file(target) else 'unchanged'}")
