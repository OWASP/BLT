from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import process

class WelcomePlugin(MachineBasePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with open("src/lettuce/plugins/welcome/welcome_message.txt", "r", encoding="utf-8") as file:
            self.welcome_message_template = file.read()

    @process("team_join")
    async def welcome(self, event):
        user_id = event['user']['id']

        response = await self.web_client.conversations_open(users=[user_id])
        dm_channel_id = response['channel']['id']

        welcome_message = self.welcome_message_template.format(user_id=user_id)

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": welcome_message.strip()
                }
            }
        ]

        await self.say(channel=dm_channel_id, text="Welcome to the OWASP Slack Community!", blocks=blocks)
