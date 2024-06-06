import json

import requests
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

repo_json_path = "/home/DonnieBLT/BLT-Lettuce/repo.json"
with open(repo_json_path) as f:
    repos_data = json.load(f)


class RepoPlugin(MachineBasePlugin):
    @command("/repo")
    async def project(self, command):
        data = requests.form
        text = data.get("text")
        user_name = data.get("user_name")
        tech_name = text.strip().lower()

        repos = repos_data.get(tech_name)

        if repos:
            repos_list = "\n".join(repos)
            message = f"Hello {user_name}, you can implement your '{tech_name}' knowledge here:\n{repos_list}"
        else:
            message = f"Hello {user_name}, the technology '{tech_name}' is not recognized. Please try again."

        command.say(message)
