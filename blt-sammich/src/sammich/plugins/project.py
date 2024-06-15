import json

from machine.clients.slack import SlackClient
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command
from machine.storage import PluginStorage
from machine.utils.collections import CaseInsensitiveDict


class ProjectPlugin(MachineBasePlugin):
    def __init__(self, client: SlackClient, settings: CaseInsensitiveDict, storage: PluginStorage):
        super().__init__(client, settings, storage)
        with open("data/projects.json") as f:
            self.project_data = json.load(f)

    @command("/project")
    async def project(self, command):
        text = command.text.strip()
        project_name = text.strip().lower()

        project = self.project_data.get(project_name)

        if project:
            project_list = "\n".join(project)
            message = (
                f"Hello, here the information about '{project_name}':\n{project_list}"
            )
        else:
            message = (
                f"Hello, the project '{project_name}' is not recognized. "
                "Please try different query."
            )

        await command.say(message)
