#!/usr/bin/env python3
"""
create_profile.py
-----------------
Parses a GitHub issue body (submitted via the add-profile issue template)
and creates/updates a profile JSON file under profiles/.

Environment variables expected:
  ISSUE_BODY   — raw issue body text
  ISSUE_AUTHOR — GitHub login of the issue author
  GH_TOKEN     — GitHub personal access token (GITHUB_TOKEN)
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _truncate(text: str, max_chars: int) -> str:
    """Truncate *text* to at most *max_chars* characters at a word boundary."""
    if len(text) <= max_chars:
        return text
    # Find the last space within the limit to avoid cutting mid-word
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "…"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_issue_body(body: str) -> dict:
    """
    Parse a GitHub Forms issue body into a key→value dict.
    GitHub renders form fields as:
        ### Label\n\nValue\n\n
    Values of '_No response_' are treated as empty.
    """
    sections: dict = {}
    pattern = r"### (.+?)\n\n(.*?)(?=\n\n###|\Z)"
    for label, value in re.findall(pattern, body, re.DOTALL):
        key = label.strip()
        val = value.strip()
        if val in ("_No response_", ""):
            val = ""
        sections[key] = val
    return sections


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def gh_get(url: str, token: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "BLT-Profiles-Action/1.0")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"[WARN] GitHub API {url} returned HTTP {exc.code}", file=sys.stderr)
        return {}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"[WARN] GitHub API request failed: {exc}", file=sys.stderr)
        return {}


def get_github_user(username: str, token: str) -> dict:
    return gh_get(f"https://api.github.com/users/{username}", token)


# ---------------------------------------------------------------------------
# Tag parsing
# ---------------------------------------------------------------------------

def parse_tags(raw: str) -> list:
    if not raw:
        return []
    return [t.strip() for t in re.split(r"[,;]+", raw) if t.strip()]

def normalize_role_section(role: str) -> str:
    """Return canonical profile section name for a submitted role."""
    if not role:
        return "Contributors"
    cleaned = role.strip().lower()
    mapping = {
        "lead": "Leads",
        "leads": "Leads",
        "co-lead": "Co-Leads",
        "co lead": "Co-Leads",
        "co-leads": "Co-Leads",
        "co leads": "Co-Leads",
        "ambassador": "Ambassadors",
        "ambassadors": "Ambassadors",
        "intern": "Interns",
        "interns": "Interns",
        "contributor": "Contributors",
        "contributors": "Contributors",
        "mentor": "Mentors",
        "mentors": "Mentors",
    }
    return mapping.get(cleaned, "Contributors")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    issue_body = os.environ.get("ISSUE_BODY", "")
    issue_author = os.environ.get("ISSUE_AUTHOR", "")
    gh_token = os.environ.get("GH_TOKEN", "")

    sections = parse_issue_body(issue_body)
    print(f"[INFO] Parsed sections: {list(sections.keys())}", file=sys.stderr)

    # Extract fields from the parsed form sections
    username = (
        sections.get("GitHub Username", "")
        or issue_author
    ).strip().lstrip("@")

    if not username:
        print("[ERROR] Could not determine GitHub username.", file=sys.stderr)
        sys.exit(1)

    role = sections.get("Role / Title", "")
    linkedin = sections.get("LinkedIn Profile URL", "")
    wallet = sections.get("Wallet / ID String", "")
    tags_raw = sections.get("Tags / Labels", "")
    involvement = sections.get(
        "Question 1: What is your involvement in cybersecurity?", ""
    )
    evolution = sections.get(
        "Question 2: How do you see cybersecurity evolving?", ""
    )
    achievement = sections.get(
        "Question 3: What is your most significant cybersecurity achievement or contribution?", ""
    )

    # Fetch live GitHub user data
    gh_user = get_github_user(username, gh_token) if gh_token else {}
    print(f"[INFO] GitHub user data fetched for '{username}'", file=sys.stderr)

    now_iso = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    profile: dict = {
        "username": username,
        "name": gh_user.get("name") or username,
        "role": role,
        "role_section": normalize_role_section(role),
        "avatar": gh_user.get("avatar_url") or f"https://github.com/{username}.png",
        "github": f"https://github.com/{username}",
        "linkedin": linkedin,
        "wallet": wallet,
        "bio": gh_user.get("bio") or "",
        "followers": gh_user.get("followers", 0),
        "following": gh_user.get("following", 0),
        "public_repos": gh_user.get("public_repos", 0),
        "questions": {
            "involvement": involvement,
            "evolution": evolution,
            "achievement": achievement,
        },
        "streak": {
            "current": 0,
            "longest": 0,
            "days_visited": 0,
            "last_visit": "",
            "last_checkin": "",
        },
        "stats": {
            "bugs_reported": 0,
            "open_issues": 0,
            "closed_issues": 0,
        },
        "issue_stats": {
            "general": 0,
            "functional": 0,
            "performance": 0,
            "security": 0,
            "typo": 0,
            "design": 0,
        },
        "bacon": {
            "earned": 0,
            "pending": 0,
            "completed": 0,
        },
        "prs": {
            "total": 0,
            "merged": 0,
            "open": 0,
            "closed": 0,
        },
        "pr_list": [],
        "badges": [],
        "tags": parse_tags(tags_raw),
        "rank": "Newcomer",
        "monthly_report": {
            "top_finding": "",
        },
        "created_at": now_iso,
    }

    # ------------------------------------------------------------------
    # Persist profile JSON
    # ------------------------------------------------------------------
    profiles_dir = Path("profiles")
    profiles_dir.mkdir(exist_ok=True)

    profile_path = profiles_dir / f"{username}.json"
    with open(profile_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)
    print(f"[INFO] Written profile → {profile_path}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Update profiles/index.json
    # ------------------------------------------------------------------
    index_path = profiles_dir / "index.json"
    if index_path.exists():
        with open(index_path, encoding="utf-8") as fh:
            index: list = json.load(fh)
    else:
        index = []

    # Upsert entry
    index = [entry for entry in index if entry.get("username") != username]
    index.append(
        {
            "username": username,
            "name": profile["name"],
            "role": profile["role"],
            "role_section": profile["role_section"],
            "avatar": profile["avatar"],
            "tags": profile["tags"],
            "stats": profile["stats"],
            "prs": profile["prs"],
            "questions": {
                "involvement": _truncate(involvement, 200),
            },
            "created_at": now_iso,
        }
    )

    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)
    print(f"[INFO] Updated index → {index_path}", file=sys.stderr)

    # Write username to a temp file so the workflow step can read it
    with open("/tmp/profile_username.txt", "w") as fh:
        fh.write(username)

    print(f"[OK] Profile created for @{username}", file=sys.stderr)


if __name__ == "__main__":
    main()