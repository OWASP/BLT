import logging
import os

import git
from flask import Flask, request
from machine.plugins.base import MachineBasePlugin

app = Flask(__name__)


class UpdateServerPlugin(MachineBasePlugin):
    @app.route("/update_server", methods=["POST"])
    def webhook(self):
        if request.method == "POST":
            current_directory = os.path.dirname(os.path.abspath(__file__))
            repo = git.Repo(current_directory)
            origin = repo.remotes.origin
            origin.pull()
            latest_commit_message = repo.head.commit.message.strip()
            self.outputs.append(
                [
                    "#slack_bot_deploys",
                    f"Deployed the latest version 1.8. Latest commit: {latest_commit_message}",
                ]
            )
            logging.info(
                f"Deployed the latest version 1.8. Latest commit: {latest_commit_message}"
            )
            return "OK", 200

        return "Error", 400
