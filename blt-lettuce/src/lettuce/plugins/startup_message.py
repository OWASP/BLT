import logging

from machine.plugins.base import MachineBasePlugin


class StartupMessagePlugin(MachineBasePlugin):
    async def init(self):
        deploys_channel_name = "#slack_bot_deploys"
        logging.info("Sent startup message to deploys channel")
        await self.say(deploys_channel_name, "Bot started v1.9 240611-1 top")
