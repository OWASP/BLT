#!/usr/bin/env python3
"""
Regenerate public/index.json and public/feed.json from public/cves/**.

Run this script after adding or modifying CVE entries, then commit
the updated public/index.json and public/feed.json alongside your changes.
"""

import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(REPO_ROOT, "public")
CVES_DIR = os.path.join(PUBLIC_DIR, "cves")
INDEX_PATH = os.path.join(PUBLIC_DIR, "index.json")
FEED_PATH = os.path.join(PUBLIC_DIR, "feed.json")

BASE_URL = os.environ.get("BLT_CVE_BASE_URL", "https://cve.owaspblt.org").rstrip("/")


def collect_entries():
    """Return a list of (id, path, entry_dict) sorted by ID."""
    entries = []
    if not os.path.isdir(CVES_DIR):
        return entries
    for year in sorted(os.listdir(CVES_DIR)):
        year_dir = os.path.join(CVES_DIR, year)
        if not os.path.isdir(year_dir):
            continue
        for fname in sorted(os.listdir(year_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(year_dir, fname)
            rel = f"/cves/{year}/{fname}"
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    entry = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"WARNING: skipping {rel}: {exc}", file=sys.stderr)
                continue
            entries.append((entry.get("id", fname[:-5]), rel, entry))
    entries.sort(key=lambda t: t[0])
    return entries


def build_index(entries, now_ts):
    return {
        "namespace": "BLT",
        "updated": now_ts,
        "count": len(entries),
        "entries": [
            {
                "id": eid,
                "path": rel,
                "severity": entry.get("severity", {}).get("cvss_score"),
            }
            for eid, rel, entry in entries
        ],
    }


def build_feed(entries, now_ts):
    return {
        "namespace": "BLT",
        "updated": now_ts,
        "count": len(entries),
        "items": [
            {
                "id": eid,
                "title": entry.get("title", ""),
                "published": entry.get("published", ""),
                "modified": entry.get("modified", ""),
                "severity": entry.get("severity", {}).get("cvss_score"),
                "url": f"{BASE_URL}{rel}",
            }
            for eid, rel, entry in entries
        ],
    }


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main():
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = collect_entries()

    index = build_index(entries, now_ts)
    feed = build_feed(entries, now_ts)

    write_json(INDEX_PATH, index)
    write_json(FEED_PATH, feed)

    print(
        f"Generated public/index.json and public/feed.json with "
        f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}."
    )


if __name__ == "__main__":
    main()
