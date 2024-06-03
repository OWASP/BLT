import requests
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

GITHUB_API_URL = "https://github.com/OWASP-BLT/BLT"

def fetch_github_data(owner, repo):
    prs = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls?state=closed"
    ).json()
    issues = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=closed"
    ).json()
    comments = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/comments"
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

    table = "User | PRs Merged | Issues Resolved | Comments\n ---- | ---------- | --------------- | --------\n"
    for user, counts in user_data.items():
        table += (
            f"{user} | {counts['prs']} | {counts['issues']} | {counts['comments']}\n"
        )

    return table

class ContributorPlugin(MachineBasePlugin):
    """Contributor plugin"""

    @command("/contributors")
    async def contributors(self, command):
        owner = "OWASP-BLT"
        repo = "BLT"

        prs, issues, comments = fetch_github_data(owner, repo)
        formatted_data = format_data(prs, issues, comments)

        await command.say(
            formatted_data or "No data available"
        )
