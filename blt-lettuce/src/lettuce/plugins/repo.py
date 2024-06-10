import json
import re
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command, action

# Load repo data from JSON file
repo_json_path = "repo.json"
with open(repo_json_path) as f:
    repos_data = json.load(f)

class RepoPlugin(MachineBasePlugin):
    @command("/repo")
    async def show_repo_options(self, command):        
        text = command.text.strip().lower()
        repos = repos_data.get(text)
        if repos:
            repos_list = "\n".join(repos)
            message = f"Hello, you can implement your '{text}' knowledge here:\n{repos_list}"
            await command.say(message)
        else:
            message_preview = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Here are the available technologies to choose from:"
                        }
                    },
                    {
                        "type": "actions",
                        "block_id": "tech_select_block",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": tech},
                                "value": tech,
                                "action_id": f"button_{tech}"
                            } for tech in repos_data.keys()
                        ]
                    }
                ]
            }

            # Ensure the channel is correctly specified as a string
            if isinstance(command.channel, str):
                channel_id = command.channel
            else:
                # Handle case where channel is not a string 
                channel_id = command.channel.id  # Access the id attribute of the Channel object

            await self.web_client.chat_postMessage(channel=channel_id, blocks=message_preview["blocks"], text="Available Technologies")

    @action(action_id=re.compile(r"button_.*"), block_id="tech_select_block")
    async def handle_button_click(self, action):
        # Extract the clicked button's value
        clicked_button_value = action.payload.actions[0].value
        repos = repos_data.get(clicked_button_value)
        repos_list = "\n".join(repos)
        message = f"Hello, you can implement your '{clicked_button_value}' knowledge here:\n{repos_list}"
        await action.say(message)
