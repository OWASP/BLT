import requests
from dotenv import dotenv_values
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

secrets = dotenv_values(".secrets")

github_token = secrets["github_token"]


class CreateIssuePlugin(MachineBasePlugin):
    @command("/ghissue")
    async def createissue(self, command):
        channel_id = command._cmd_payload["channel_id"]
        title = command.text.strip()

        # Replace with your repository details
        owner = "OWASP-BLT"
        repo = "BLT-Sammich"

        # GitHub API endpoint for creating an issue
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"

        # Headers including Authorization with token and specifying API version
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Issue data: only title
        issue_data = {
            "title": title,
            "body": "",
            "assignee": None,
            "milestone": None,
        }

        try:
            response = requests.post(url, headers=headers, json=issue_data)
            response.raise_for_status()
            issue_url = response.json().get("html_url", "No URL found")
            await self.say(channel_id, f"Issue created successfully: {issue_url}")
        except requests.exceptions.RequestException as e:
            # Log the full response for debugging
            print(response.content)
            await self.say(channel_id, f"Failed to create issue: {str(e)}")
