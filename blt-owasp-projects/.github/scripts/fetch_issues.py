import requests
import json
import os
import time

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "OWASP"
OUTPUT_FILE = "issues.json"
KNOWN_IDS_FILE = "known_issue_ids.json"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_NEW_ISSUES_WEBHOOK")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")

headers = {"Accept": "application/vnd.github.v3+json"}
if ACCESS_TOKEN:
    headers["Authorization"] = f"token {ACCESS_TOKEN}"


def load_existing_issue_ids():
    """Load all issue IDs ever seen (to avoid duplicate Slack notifications)."""
    try:
        with open(KNOWN_IDS_FILE, "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        # Fall back to current issues.json if known_issue_ids.json doesn't exist yet
        try:
            with open(OUTPUT_FILE, "r") as f:
                existing = json.load(f)
                return {issue["id"] for issue in existing}
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return set()


def save_known_issue_ids(existing_ids, new_ids):
    """Persist the union of all seen issue IDs."""
    combined = sorted(existing_ids | new_ids)
    with open(KNOWN_IDS_FILE, "w") as f:
        json.dump(combined, f)


def fetch_issues():
    all_issues = []
    page = 1

    while True:
        url = f"{GITHUB_API_URL}/search/issues"
        params = {
            "q": f"org:{ORG_NAME} is:issue state:open",
            "sort": "updated",
            "order": "desc",
            "per_page": 100,
            "page": page,
        }
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 422:
            print(f"Validation error on page {page}, stopping: {response.text}")
            break

        if response.status_code != 200:
            print(f"Error fetching issues page {page}: {response.status_code} {response.text}")
            break

        data = response.json()
        items = data.get("items", [])

        if not items:
            break

        all_issues.extend(items)
        print(f"  Fetched page {page}: {len(items)} issues (total so far: {len(all_issues)})")

        # GitHub search API caps at 1000 results
        if len(all_issues) >= 1000:
            break

        page += 1
        # Respect rate limits
        time.sleep(1)

    return all_issues


def format_issue(issue):
    repo_url = issue.get("repository_url", "")
    repo_name = "/".join(repo_url.split("/")[-2:]) if repo_url else ""

    labels = [{"name": lbl["name"], "color": lbl["color"]} for lbl in issue.get("labels", [])]
    assignees = [a["login"] for a in issue.get("assignees", [])]
    milestone = issue.get("milestone", {})

    return {
        "id": issue["id"],
        "number": issue["number"],
        "repo": repo_name,
        "title": issue["title"],
        "state": issue["state"],
        "author": issue["user"]["login"] if issue.get("user") else "",
        "author_url": issue["user"]["html_url"] if issue.get("user") else "",
        "labels": labels,
        "assignees": assignees,
        "milestone": milestone.get("title", "") if milestone else "",
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "comments": issue["comments"],
        "html_url": issue["html_url"],
    }


def send_slack_notification(issue):
    if not SLACK_WEBHOOK_URL:
        print("No SLACK_NEW_ISSUES_WEBHOOK set, skipping Slack notification")
        return

    repo = issue["repo"]
    labels_text = ", ".join(lbl["name"] for lbl in issue["labels"]) if issue["labels"] else "none"
    assignees_text = ", ".join(issue["assignees"]) if issue["assignees"] else "unassigned"

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f":new: New issue in *{repo}*\n"
                        f"*<{issue['html_url']}|#{issue['number']}: {issue['title']}>*\n"
                        f"Author: `{issue['author']}` | Labels: `{labels_text}` | Assignees: `{assignees_text}`"
                    ),
                },
            }
        ]
    }

    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        print(f"Failed to send Slack notification: {response.status_code} {response.text}")


def main():
    print(f"Loading existing issue IDs from {OUTPUT_FILE}...")
    existing_ids = load_existing_issue_ids()
    print(f"Found {len(existing_ids)} existing issues")

    print(f"Fetching open issues from OWASP organization...")
    raw_issues = fetch_issues()
    print(f"Fetched {len(raw_issues)} issues total")

    formatted_issues = [format_issue(issue) for issue in raw_issues]

    new_issues = [issue for issue in formatted_issues if issue["id"] not in existing_ids]
    print(f"Found {len(new_issues)} new issues")

    new_ids = {issue["id"] for issue in new_issues}
    for issue in new_issues:
        print(f"  New: #{issue['number']} in {issue['repo']}: {issue['title']}")
        send_slack_notification(issue)

    save_known_issue_ids(existing_ids, new_ids)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(formatted_issues, f, indent=2)

    print(f"Wrote {len(formatted_issues)} issues to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()