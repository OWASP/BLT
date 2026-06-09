#!/usr/bin/env python3
"""Validate the static UI contract for the BLT-Hackathons redesign.

This intentionally checks for the shared theme assets, required landing-page
sections, required dashboard dynamic IDs, and obvious secret leaks. It is a
lightweight regression guard for a static HTML/JS project without a frontend
build/test runner.
"""

from __future__ import annotations

import re
import sys
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "public/css/blt-theme.css",
    "public/js/theme.js",
    "public/index.html",
    "public/hackathon.html",
    "public/js/index.js",
    "public/js/main.js",
]

INDEX_REQUIRED_IDS = [
    "site-header",
    "site-title",
    "hero-title",
    "hero-description",
    "platform-stats",
    "platform-stats-grid",
    "featured-event",
    "featured-event-content",
    "hackathons-grid",
    "no-hackathons",
    "events",
    "how-it-works",
    "gsoc-warmup",
    "provider-support",
    "maintainer-cta",
    "site-footer",
]

DASHBOARD_REQUIRED_IDS = [
    "hackathon-title",
    "nav-title",
    "hackathon-status",
    "banner-section",
    "hackathon-name",
    "hackathon-dates",
    "time-remaining",
    "participant-count",
    "pr-count",
    "merged-pr-count",
    "issue-count",
    "repo-count",
    "days-active-count",
    "prActivityChart",
    "leaderboard",
    "review-leaderboard",
    "repositories-list",
    "sponsors-list",
    "hackathon-description",
    "rules-section",
    "hackathon-rules",
    "timeline-panel",
    "timeline-progress-bar",
    "timeline-progress-label",
    "timeline-start-date",
    "timeline-current-date",
    "timeline-end-date",
    "data-freshness",
]

INDEX_REQUIRED_TEXT = [
    "BLT Hackathons",
    "contribution",
    "Featured event",
    "GSoC",
    "GitLab",
    "OWASP BLT ecosystem",
]

INDEX_REQUIRED_SNIPPETS = [
    "filterHackathons('all')",
    "filterHackathons('ongoing')",
    "filterHackathons('upcoming')",
    "filterHackathons('ended')",
    "data-theme-toggle",
    "position: sticky",
]

DASHBOARD_REQUIRED_TEXT = [
    "Back to events",
    "Source",
    "Contribute",
    "Event timeline",
    "Activity trend",
    "Leaderboard",
    "Review",
    "About",
    "Rules",
    "Eligible repositories",
    "Sponsors & prizes",
    "Data freshness",
]

DASHBOARD_REQUIRED_SNIPPETS = [
    "position: sticky",
    "data-theme-toggle",
    "id=\"prActivityChart\"",
    "openSponsorModal()",
]

SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"glpat-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"GITHUB_TOKEN\s*=\s*['\"][^'\"]+['\"]"),
    re.compile(r"GITLAB_TOKEN\s*=\s*['\"][^'\"]+['\"]"),
    re.compile(r"PRIVATE-TOKEN\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def has_id(markup: str, element_id: str) -> bool:
    return bool(re.search(rf"\bid\s*=\s*(['\"])" + re.escape(element_id) + r"\1", markup))


def main() -> int:
    failures: list[str] = []

    for relative_path in REQUIRED_FILES:
        if not (ROOT / relative_path).exists():
            failures.append(f"missing required file: {relative_path}")

    index = read("public/index.html") if (ROOT / "public/index.html").exists() else ""
    dashboard = read("public/hackathon.html") if (ROOT / "public/hackathon.html").exists() else ""
    dashboard_text = unescape(dashboard)
    theme_js = read("public/js/theme.js") if (ROOT / "public/js/theme.js").exists() else ""

    if index:
        if "css/blt-theme.css" not in index:
            failures.append("public/index.html must load css/blt-theme.css")
        if "js/theme.js" not in index:
            failures.append("public/index.html must load js/theme.js")
        for element_id in INDEX_REQUIRED_IDS:
            if not has_id(index, element_id):
                failures.append(f"public/index.html missing id={element_id}")
        for text in INDEX_REQUIRED_TEXT:
            if text.lower() not in index.lower():
                failures.append(f"public/index.html missing expected text: {text}")
        for snippet in INDEX_REQUIRED_SNIPPETS:
            if snippet not in index:
                failures.append(f"public/index.html missing expected snippet: {snippet}")

    if dashboard:
        if "css/blt-theme.css" not in dashboard:
            failures.append("public/hackathon.html must load css/blt-theme.css")
        if "js/theme.js" not in dashboard:
            failures.append("public/hackathon.html must load js/theme.js")
        for element_id in DASHBOARD_REQUIRED_IDS:
            if not has_id(dashboard, element_id):
                failures.append(f"public/hackathon.html missing id={element_id}")
        for text in DASHBOARD_REQUIRED_TEXT:
            if text.lower() not in dashboard_text.lower():
                failures.append(f"public/hackathon.html missing expected text: {text}")
        for snippet in DASHBOARD_REQUIRED_SNIPPETS:
            if snippet not in dashboard:
                failures.append(f"public/hackathon.html missing expected snippet: {snippet}")

    if theme_js and "blt-theme" not in theme_js:
        failures.append("public/js/theme.js must use localStorage key blt-theme")

    scanned_paths = [
        "public/index.html",
        "public/hackathon.html",
        "public/js/index.js",
        "public/js/main.js",
        "public/js/theme.js",
        "public/css/blt-theme.css",
    ]
    for relative_path in scanned_paths:
        path = ROOT / relative_path
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                failures.append(f"possible secret/token pattern in {relative_path}: {pattern.pattern}")

    if failures:
        print("UI contract validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("UI contract validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
