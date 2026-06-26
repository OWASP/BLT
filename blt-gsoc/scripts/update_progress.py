#!/usr/bin/env python3
"""Fill in the GSoC 2026 progress tracker data for one day.

For every contributor in data/contributors.json, this script queries the
GitLab API for their commits in OWASP-BLT project repositories and the Slack
search API (on both workspaces) for messages on the given day (default: today,
UTC), then saves the result into data/progress.json, which progress-tracker.html
renders:

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

- commits  : total commits authored by the user that day in their repo(s)
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


def day_window(day):
    start = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    return (
        start.isoformat().replace("+00:00", "Z"),
        end.isoformat().replace("+00:00", "Z"),
    )


def gitlab_project_paths(contributor):
    repos = contributor.get("repos") or [contributor.get("repo") or contributor.get("project")]
    return [f"OWASP-BLT/{repo}" for repo in repos if repo]


def normalized_identity(value):
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def email_localpart(value):
    return str(value or "").split("@", 1)[0]


def commit_author_aliases(contributor):
    aliases = {
        contributor.get("name"),
        contributor.get("github"),
        contributor.get("gitlab"),
        email_localpart(contributor.get("github")),
        email_localpart(contributor.get("gitlab")),
    }
    aliases.update(contributor.get("commit_authors") or [])
    return {normalized_identity(alias) for alias in aliases if alias}


def commit_matches_contributor(commit, contributor):
    aliases = commit_author_aliases(contributor)
    commit_identities = {
        commit.get("author_name"),
        commit.get("committer_name"),
        email_localpart(commit.get("author_email")),
        email_localpart(commit.get("committer_email")),
    }
    return any(normalized_identity(identity) in aliases for identity in commit_identities if identity)


def project_commits_for_day(project_path, day):
    """All commits created in an OWASP-BLT project repository on `day`."""
    start, end = day_window(day)
    project_id = urllib.parse.quote(project_path, safe="")
    commits = []
    page = 1
    while True:
        try:
            batch = api_get(
                f"/projects/{project_id}/repository/commits",
                {
                    "all": "true",
                    "since": start,
                    "until": end,
                    "per_page": 100,
                    "page": page,
                },
            )
        except urllib.error.HTTPError as error:
            print(f"  warning: GitLab API {error.code} for {project_path}", file=sys.stderr)
            return []
        commits.extend(batch)
        if len(batch) < 100:
            return commits
        page += 1


def commits_for_day(contributor, day):
    return sum(
        1
        for project_path in gitlab_project_paths(contributor)
        for commit in project_commits_for_day(project_path, day)
        if commit_matches_contributor(commit, contributor)
    )


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


def slack_for_day(slack_info, day):
    result = {}
    for server, env_var in SLACK_SERVERS.items():
        token = os.environ.get(env_var)
        # Support either a single string username or a dictionary: {"owasp": "user1", "blt": "user2"}
        username = slack_info.get(server) if isinstance(slack_info, dict) else slack_info
        if token and username:
            result[server] = slack_sent_message(token, username, day)
        else:
            result[server] = False
    return result


def progress_for_day(contributor, day):
    slack = slack_for_day(contributor.get("slack", ""), day)
    return {
        "commits": commits_for_day(contributor, day),
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
