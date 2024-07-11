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

        github = Github(github_token)

        try:
            repo = github.get_repo(
                f"{settings.GITHUB_REPOSITORY_OWNER}/{settings.GITHUB_REPOSITORY_NAME}"
            )
            issue = repo.create_issue(title=title)
            await self.say(channel_id, f"Issue created successfully: {issue.html_url}")
        except Exception:
            logging.error("Failed to create issue")
            await self.say(channel_id, "Failed to create issue")


# Initialize logging
logging.basicConfig(level=logging.INFO)
