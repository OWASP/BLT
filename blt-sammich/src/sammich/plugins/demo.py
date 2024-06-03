from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command


class DemoPlugin(MachineBasePlugin):
    """Demo plugin"""

    @command("/demo")
    async def demo(self, command):
        await command.say("This is a demo response!")
