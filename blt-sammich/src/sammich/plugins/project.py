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
        with open("data/projects.json") as f:
            self.project_data = json.load(f)

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
            await self.show_project_page(channel_id)

    async def show_project_page(self, channel_id):
        projects = list(self.project_data.keys())

        if not projects:
            await self.web_client.chat_postMessage(
                channel=channel_id, text="No projects available."
            )
            return

        # Calculate the number of dropdowns needed
        num_dropdowns = (len(projects) + PROJECTS_PER_PAGE - 1) // PROJECTS_PER_PAGE

        blocks = []
        for i in range(num_dropdowns):
            start_index = i * PROJECTS_PER_PAGE
            end_index = start_index + PROJECTS_PER_PAGE
            project_slice = projects[start_index:end_index]

            options = [
                {"text": {"type": "plain_text", "text": project[:75]}, "value": project}
                for project in project_slice
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

        await self.web_client.chat_postMessage(
            channel=channel_id, blocks=blocks, text="Available Projects"
        )


    @action(action_id=re.compile(r"project_select_action_.*"), block_id=None)
    async def handle_dropdown_selection(self, action):
        selected_project = action.payload.actions[0].selected_option.value
        project = self.project_data.get(selected_project)
        project_list = "\n".join(project)
        message = f"Hello, here is the information about '{selected_project}':\n{project_list}"
        await action.say(message)