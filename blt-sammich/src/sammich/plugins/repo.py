import json
import re

from machine.clients.slack import SlackClient
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import action, command
from machine.storage import PluginStorage
from machine.utils.collections import CaseInsensitiveDict


class RepoPlugin(MachineBasePlugin):
    def __init__(self, client: SlackClient, settings: CaseInsensitiveDict, storage: PluginStorage):
        super().__init__(client, settings, storage)
        with open("data/repos.json") as f:
            self.repo_data = json.load(f)

    @command("/repo")
    async def repo(self, command):
        tech_name = command.text.strip().lower()
        channel_id = command._cmd_payload["channel_id"]

        repos = self.repo_data.get(tech_name)
        if repos:
            repos_list = "\n".join(repos)
            message = f"Hello, you can implement your '{tech_name}' knowledge here:\n{repos_list}"
            await command.say(message)
        else:
            fallback_message = "Available technologies:"
            message_preview = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Here are the available technologies to choose from:",
                        },
                    },
                    {
                        "type": "actions",
                        "block_id": "tech_select_block",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": tech},
                                "value": tech,
                                "action_id": f"plugin_repo_button_{tech}",
                            }
                            for tech in self.repo_data.keys()
                        ],
                    },
                ]
            }

            await self.web_client.chat_postMessage(
                channel=channel_id,
                blocks=message_preview["blocks"],
                text=fallback_message,
            )

    @action(action_id=re.compile(r"plugin_repo_button_.*"), block_id=None)
    async def handle_button_click(self, action):
        clicked_button_value = action.payload.actions[0].value
        repos = self.repo_data.get(clicked_button_value)
        repos_list = "\n".join(repos)
        message = (
            f"Hello, you can implement your '{clicked_button_value}' knowledge here:\n{repos_list}"
        )
        await action.say(message)
