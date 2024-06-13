import logging

from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import respond_to
from slack_sdk.errors import SlackApiError

# Constants for channel code and error channel ID
CONTRIBUTE_CHANNEL_CODE = "C077QBBLY1Z"
ERROR_CHANNEL_ID = "#project-blt-lettuce-deploys"


class HandleMessagesPlugin(MachineBasePlugin):
    @respond_to(r"(contribute|contributing|contributes)")
    async def handle_messages(self, msg, *args):
        try:
            await msg.reply(
                f"Please check the channel <#{CONTRIBUTE_CHANNEL_CODE}>"
                "for contributing guidelines today!"
            )
        except SlackApiError as e:
            logging.error(f"Error sending contribution message: {e.response['error']}")
            await self.say(ERROR_CHANNEL_ID, f"Error sending message : {e.response['error']}")
