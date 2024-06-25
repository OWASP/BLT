import os

import requests
from dotenv import load_dotenv
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

load_dotenv()

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def fetch_github_data(owner, repo):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    prs = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls?state=closed", headers=headers
    ).json()
    issues = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=closed", headers=headers
    ).json()
    comments = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/comments", headers=headers
    ).json()
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
    max_comments_length = max(
        max(len(str(counts["comments"])) for counts in user_data.values()), 9
    )

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


class ContributorPlugin(MachineBasePlugin):
    """Contributor plugin"""

    @command("/contributors")
    async def contributors(self, command):
        prs, issues, comments = fetch_github_data("OWASP-BLT", "BLT")
        formatted_data = format_data(prs, issues, comments)
        if not formatted_data:
            formatted_data = [
                {"type": "section", "text": {"type": "mrkdwn", "text": "No data available"}}
            ]

        await command.say(text="Contributors Activity", blocks=formatted_data)
