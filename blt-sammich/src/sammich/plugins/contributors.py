import requests
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

GITHUB_API_URL = "https://api.github.com"


def fetch_github_data(owner, repo):
    prs = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls?state=closed").json()
    issues = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=closed").json()
    comments = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/comments").json()
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

    max_name_length = max(len(user) for user in user_data.keys())
    max_prs_length = max(len(str(counts["prs"])) for counts in user_data.values())
    max_issues_length = max(len(str(counts["issues"])) for counts in user_data.values())
    max_comments_length = max(len(str(counts["comments"])) for counts in user_data.values())

    table = [
        f"| {'User':<{max_name_length}} | PRs Merged | Issues Resolved | Comments |",
        f"|{'-' * (max_name_length + 2)}|:{'-' * (max_prs_length + 2)}:|"
        f":{'-' * (max_issues_length + 2)}:|:{'-' * (max_comments_length + 2)}:|",
    ]
    for user, counts in user_data.items():
        table.append(
            f"| {user:<{max_name_length}} | {counts['prs']:>{max_prs_length}} | "
            f"{counts['issues']:>{max_issues_length}} | "
            f"{counts['comments']:>{max_comments_length}} |"
        )

    return "\n".join(table)


class ContributorPlugin(MachineBasePlugin):
    """Contributor plugin"""

    @command("/contributors")
    async def contributors(self, command):
        formatted_data = {}
        try:
            prs, issues, comments = fetch_github_data("OWASP-BLT", "BLT")
            formatted_data = format_data(prs, issues, comments)
        except requests.exceptions.JSONDecodeError:
            pass

        await command.say(formatted_data or "No data available")
