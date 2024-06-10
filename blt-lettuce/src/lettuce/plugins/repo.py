import json

from machine.clients.slack import SlackClient
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command
from machine.storage import PluginStorage
from machine.utils.collections import CaseInsensitiveDict

repo_json_path = "data/repos.json"
with open(repo_json_path) as f:
    repos_data = json.load(f)


class RepoPlugin(MachineBasePlugin):
    def __init__(self, client: SlackClient, settings: CaseInsensitiveDict, storage: PluginStorage):
        super().__init__(client, settings, storage)

        with open("data/repos.json") as f:
            self.repo_data = json.load(f)

    @command("/repo")
    async def repo(self, command):
        tech_name = command.text.strip().lower()

        repos = self.repo_data.get(tech_name)
        if repos:
            repos_list = "\n".join(repos)
            message = f"Hello, you can implement your '{tech_name}' knowledge here:\n{repos_list}"
        else:
            message = f"Hello, the technology '{tech_name}' is not recognized. Please try again."
        await command.say(message)
