import json
import re

from machine.clients.slack import SlackClient
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import action, command
from machine.storage import PluginStorage
from machine.utils.collections import CaseInsensitiveDict

PROJECTS_PER_PAGE = 100


class ProjectPlugin(MachineBasePlugin):
    def __init__(self, client: SlackClient, settings: CaseInsensitiveDict, storage: PluginStorage):
        super().__init__(client, settings, storage)

        try:
            with open("data/projects.json") as f:
                self.project_data = json.load(f)
        except json.JSONDecodeError:
            self.project_data = {}

    @command("/project")
    async def project(self, command):
        project_name = command.text.strip().lower()
        channel_id = command._cmd_payload["channel_id"]

        project = self.project_data.get(project_name)

        if project:
            project_list = "\n".join(project)
            message = f"Hello, here the information about '{project_name}':\n{project_list}"
            await command.say(message)
        else:
            # if the self.project_data is empty, return a message
            if not self.project_data:
                await command.say("No projects available")
                return None
            await self.show_project_page(channel_id)

    async def show_project_page(self, channel_id):
        projects = list(self.project_data.keys())

        # Calculate the number of dropdowns needed
        num_dropdowns = (len(projects) + PROJECTS_PER_PAGE - 1) // PROJECTS_PER_PAGE

        blocks = []
        project_for_each_page = 75
        for i in range(num_dropdowns):
            options = [
                {
                    "text": {"type": "plain_text", "text": project[:project_for_each_page]},
                    "value": project,
                }
                for project in projects[
                    i * PROJECTS_PER_PAGE : i * PROJECTS_PER_PAGE + PROJECTS_PER_PAGE
                ]
            ]

            blocks.append(
                {
                    "type": "section",
                    "block_id": f"project_select_block_{i}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Select a project (Page {i + 1}):",
                    },
                    "accessory": {
                        "type": "static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": f"Select a project (Page {i + 1})",
                        },
                        "options": options,
                        "action_id": f"project_select_action_{i}",
                    },
                }
            )

        # Here, we use `self.web_client.chat_postMessage` instead of `command.say()` 
        # because `command.say()` sends an ephemeral message (is_ephemeral=True) by default. 
        # When is_ephemeral is true, Slack API restricts interactions with the message, 
        # making it impossible to trigger actions from it. 
        # Therefore, we use `web_client.chat_postMessage` to post a standard message 
        # that allows interactive elements like dropdowns to work correctly.
        await self.web_client.chat_postMessage(
            channel=channel_id, blocks=blocks, text="Available Projects"
        )

    @action(action_id=re.compile(r"project_select_action_.*"))
    async def handle_dropdown_selection(self, action):
        selected_project = action.payload.actions[0].selected_option.value
        project = self.project_data.get(selected_project)
        project_list = "\n".join(project)
        message = f"Hello, here is the information about '{selected_project}':\n{project_list}"
        await action.say(message)
