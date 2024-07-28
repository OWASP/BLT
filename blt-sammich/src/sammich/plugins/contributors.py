import os

import requests
from dotenv import dotenv_values
secrets = dotenv_values(".secrets")

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = secrets["GITHUB_TOKEN"]


def fetch_github_data(owner, repo, since_date):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        prs = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls?state=merged&since={since_date}", headers=headers).json()
        issues = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=closed&since={since_date}", headers=headers).json()
        comments = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/comments?&since={since_date}", headers=headers).json()
    except requests.RequestException as e:
        print(f"Error fetching GitHub data: {e}")
        return [], [], []
    return prs, issues, comments

def format_data(prs, issues, comments):
    user_data = {}

    for pr in prs:
        user = pr["user"]["login"]
        if user not in user_data:
            user_data[user] = {"prs": 0, "issues": 0, "comments": 0}
        user_data[user]["prs"] += 1

    for issue in issues:
        user = issue["user"]["login"]
        if user not in user_data:
            user_data[user] = {"prs": 0, "issues": 0, "comments": 0}
        user_data[user]["issues"] += 1

    for comment in comments:
        user = comment["user"]["login"]
        if user not in user_data:
            user_data[user] = {"prs": 0, "issues": 0, "comments": 0}
        user_data[user]["comments"] += 1

    # Calculate column widths with minimum lengths
    max_user_length = max(len(user) for user in user_data.keys())
    max_prs_length = max(max(len(str(counts["prs"])) for counts in user_data.values()), 10)
    max_issues_length = max(max(len(str(counts["issues"])) for counts in user_data.values()), 15)
    max_comments_length = max(max(len(str(counts["comments"])) for counts in user_data.values()), 9)

    # Formatting table header
    header = (
        f"{'User':<{max_user_length}}  "
        f"{'PRs Merged':<{max_prs_length}}  "
        f"{'Issues Resolved':<{max_issues_length}}  "
        f"{'Comments':<{max_comments_length}}\n"
    )
    separator = (
        f"{'-' * max_user_length}  "
        f"{'-' * max_prs_length}  "
        f"{'-' * max_issues_length}  "
        f"{'-' * max_comments_length}\n"
    )
    rows = [header, separator]

    # Formatting each user's data
    for user, counts in user_data.items():
        rows.append(
            f"{user:<{max_user_length}}  "
            f"{counts['prs']:<{max_prs_length}}  "
            f"{counts['issues']:<{max_issues_length}}  "
            f"{counts['comments']:<{max_comments_length}}\n"
        )

    table = "".join(rows)

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Contributor Data*\n```\n{table}\n```"},
        }
    ]
