import json

from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

repo_json_path = "repo.json"
with open(repo_json_path) as f:
    repos_data = json.load(f)


class RepoPlugin(MachineBasePlugin):
    @command("/repo")
    async def repo(self, command):
        text = command.text.strip()
        tech_name = text.lower()
        repos = repos_data.get(tech_name)
        if repos:
            repos_list = "\n".join(repos)
            message = f"Hello, you can implement your '{tech_name}' knowledge here:\n{repos_list}"
        else:
            message = f"Hello , the technology '{tech_name}' is not recognized. Please try again."
        await command.say(message)
