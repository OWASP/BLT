#!/usr/bin/env python3
"""Fill in the GSoC 2026 progress tracker data for one day.

For every contributor in data/contributors.json, this script queries the
GitLab events API for their commits and the Slack search API (on both
workspaces) for messages on the given day (default: today, UTC), then saves
the result into data/progress.json, which progress-tracker.html renders:

    {
        "updated": "2026-06-11T18:00:00+00:00",
        "days": {
            "2026-06-11": {
                "Pritz395": {
                    "commits": 3,
                    "checkin": true,
                    "slack": { "owasp": true, "blt": false }
                }
            }
        }
    }

- commits  : total commits pushed by the user that day (push events)
- slack    : per workspace, true if the user sent a message that day
- checkin  : true if the user sent a message in either workspace

Existing days in progress.json are preserved; only the requested day is
overwritten. Intended to run from the scheduled GitLab CI job (see
.gitlab-ci.yml), but works locally too:

    python3 scripts/update_progress.py             # today (UTC)
    python3 scripts/update_progress.py --date 2026-06-11

Environment variables:
    GITLAB_TOKEN       - optional, raises GitLab API rate limits
    SLACK_TOKEN_OWASP  - user token (search:read) for the OWASP workspace
    SLACK_TOKEN_BLT    - user token (search:read) for the BLT workspace
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRIBUTORS_FILE = os.path.join(ROOT, "data", "contributors.json")
PROGRESS_FILE = os.path.join(ROOT, "data", "progress.json")
GITLAB_API = os.environ.get("GITLAB_API", "https://gitlab.com/api/v4")

# The two Slack workspaces we track, mapped to the env var holding the
# user token (search:read scope) for each.
SLACK_SERVERS = {
    "owasp": "SLACK_TOKEN_OWASP",
    "blt": "SLACK_TOKEN_BLT",
}


def api_get(path, params):
    url = f"{GITLAB_API}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "BLT-GSOC-progress-tracker"})
    token = os.environ.get("GITLAB_TOKEN")
    if token:
        request.add_header("PRIVATE-TOKEN", token)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def events_for_day(username, day):
    """All events for a user on `day` (the API's after/before are exclusive)."""
    events = []
    page = 1
    while True:
        try:
            batch = api_get(
                f"/users/{urllib.parse.quote(username)}/events",
                {
                    "after": (day - dt.timedelta(days=1)).isoformat(),
                    "before": (day + dt.timedelta(days=1)).isoformat(),
                    "per_page": 100,
                    "page": page,
                },
            )
        except urllib.error.HTTPError as error:
            print(f"  warning: GitLab API {error.code} for {username}", file=sys.stderr)
            return []
        events.extend(batch)
        if len(batch) < 100:
            return events
        page += 1


def commits_for_day(username, day):
    commits = 0
    for event in events_for_day(username, day):
        if event.get("action_name", "").startswith("pushed"):
            commits += (event.get("push_data") or {}).get("commit_count") or 0
    return commits


def slack_sent_message(token, username, day):
    """True if the user sent at least one message in the workspace on `day`."""
    params = {
        "query": f"from:@{username} on:{day.isoformat()}",
        "count": 1,
    }
    url = f"https://slack.com/api/search.messages?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BLT-GSOC-progress-tracker",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
    except urllib.error.URLError as error:
        print(f"  warning: Slack API error for {username}: {error}", file=sys.stderr)
        return False
    if not data.get("ok"):
        print(f"  warning: Slack API: {data.get('error')} for {username}", file=sys.stderr)
        return False
    return (data.get("messages", {}).get("total") or 0) > 0


def slack_for_day(username, day):
    result = {}
    for server, env_var in SLACK_SERVERS.items():
        token = os.environ.get(env_var)
        if token and username:
            result[server] = slack_sent_message(token, username, day)
        else:
            result[server] = False
    return result


def progress_for_day(contributor, day):
    gitlab = contributor.get("gitlab") or contributor["github"]
    slack = slack_for_day(contributor.get("slack", ""), day)
    return {
        "commits": commits_for_day(gitlab, day),
        "checkin": any(slack.values()),
        "slack": slack,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="day to update as YYYY-MM-DD (default: today, UTC)")
    args = parser.parse_args()

    day = (
        dt.date.fromisoformat(args.date)
        if args.date
        else dt.datetime.now(dt.timezone.utc).date()
    )

    with open(CONTRIBUTORS_FILE) as f:
        contributors = json.load(f)
    try:
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        progress = {}
    progress.setdefault("days", {})

    day_key = day.isoformat()
    day_data = {}
    for contributor in contributors:
        github = contributor["github"]
        day_data[github] = progress_for_day(contributor, day)
        print(f"{day_key} {github}: {day_data[github]}")

    progress["days"][day_key] = day_data
    progress["days"] = dict(sorted(progress["days"].items()))
    progress["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)
        f.write("\n")
    print(f"saved {PROGRESS_FILE}")


if __name__ == "__main__":
    main()
