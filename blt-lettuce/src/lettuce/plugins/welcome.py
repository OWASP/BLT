from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import process


class WelcomePlugin(MachineBasePlugin):
    @process("team_join")
    async def welcome(self, event):
        user_id = event['user']['id']

        response = await self.web_client.conversations_open(users=[user_id])
        dm_channel_id = response['channel']['id']

        welcome_message = self.get_welcome_message(user_id)

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


    def get_welcome_message(self, user_id):
        with open("welcome_message.txt", "r", encoding="utf-8") as file:
            message = file.read()
        return message.format(user_id=user_id)