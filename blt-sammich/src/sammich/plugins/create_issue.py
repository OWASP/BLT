import logging

from dotenv import dotenv_values
from github import Github
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

import settings

# Load secrets
secrets = dotenv_values(".secrets")
github_token = secrets["github_token"]


class CreateIssuePlugin(MachineBasePlugin):
    @command("/ghissue")
    async def createissue(self, command):
        channel_id = command._cmd_payload["channel_id"]
        title = command.text.strip()

        g = Github(github_token)

        try:
            repo = g.get_repo(f"{settings.owner}/{settings.repo}")
            issue = repo.create_issue(title=title)
            issue_url = issue.html_url
            await self.say(channel_id, f"Issue created successfully: {issue_url}")
        except Exception as e:
            logging.error(f"Failed to create issue: {str(e)}")
            await self.say(channel_id, f"Failed to create issue: {str(e)}")


# Initialize logging
logging.basicConfig(level=logging.INFO)
