import json
import logging
import re
from datetime import datetime, timedelta

from dotenv import dotenv_values
from github import Github
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.app import App

import settings
from src.sammich.plugins.contributors import fetch_github_data, format_data
from src.sammich.plugins.project import show_project_page

PROJECTS_PER_PAGE = 100
# Load environment variables
secrets = dotenv_values(".secrets")

SLACK_APP_TOKEN = secrets["SLACK_APP_TOKEN"]
SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]
GITHUB_TOKEN = secrets["GITHUB_TOKEN"]

# Initialize Slack App
app = App(token=SLACK_BOT_TOKEN)


@app.command("/contributors")
def contributors(ack, say, command):
    ack()
    since_date = (datetime.now() - timedelta(days=7)).date()
    prs, issues, comments = fetch_github_data("OWASP-BLT", "Lettuce", since_date)
    formatted_data = format_data(prs, issues, comments)
    if not formatted_data:
        formatted_data = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "No data available"}}
        ]
    say(text="Contributors Activity", blocks=formatted_data)


@app.command("/ghissue")
async def createissue(self, command):
    channel_id = command._cmd_payload["channel_id"]
    title = command.text.strip()
    github = Github(GITHUB_TOKEN)
    try:
        repo = github.get_repo(
            f"{settings.GITHUB_REPOSITORY_OWNER}/{settings.GITHUB_REPOSITORY_NAME}"
        )
        issue = repo.create_issue(title=title)
        await self.say(channel_id, f"Issue created successfully: {issue.html_url}")
    except Exception:
        logging.error("Failed to create issue")
        await self.say(channel_id, "Failed to create issue")


with open("data/projects.json") as f:
    project_data = json.load(f)

with open("data/repos.json") as f:
    repo_data = json.load(f)


@app.command("/project")
def project(ack, command, say):
    ack()  # Acknowledge the command
    project_name = command["text"].strip().lower()
    channel_id = command["channel_id"]
    project = project_data.get(project_name)
    if project:
        project_list = "\n".join(project)
        message = f"Hello, here is the information about '{project_name}':\n{project_list}"
        say(message)
    else:
        show_project_page(channel_id, say)


@app.action(re.compile(r"project_select_action_.*"))
def handle_dropdown_selection(ack, body, say):
    ack()  # Acknowledge the interaction
    selected_project = body["actions"][0]["selected_option"]["value"]
    project = project_data.get(selected_project)
    project_list = "\n".join(project)
    message = f"Hello, here is the information about '{selected_project}':\n{project_list}"
    say(message)


@app.command("/repo")
def repo(ack, command, say):
    ack()
    tech_name = command["text"].strip().lower()
    channel_id = command["channel_id"]

    repos = repo_data.get(tech_name)
    if repos:
        repos_list = "\n".join(repos)
        message = f"Hello, you can implement your '{tech_name}' knowledge here:\n{repos_list}"
        say(message)
    else:
        fallback_message = "Available technologies:"
        message_preview = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Here are the available technologies to choose from:",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "tech_select_block",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": tech},
                            "value": tech,
                            "action_id": f"plugin_repo_button_{tech}",
                        }
                        for tech in repo_data.keys()
                    ],
                },
            ]
        }

        say(
            channel=channel_id,
            blocks=message_preview["blocks"],
            text=fallback_message,
        )


@app.action(re.compile(r"plugin_repo_button_.*"))
def handle_button_click(ack, body, say):
    ack()
    clicked_button_value = body["actions"][0]["value"]
    repos = repo_data.get(clicked_button_value)
    repos_list = "\n".join(repos)
    message = (
        f"Hello, you can implement your '{clicked_button_value}' knowledge here:\n{repos_list}"
    )
    say(message)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
