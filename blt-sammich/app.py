import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify
from slack import WebClient
from slackeventsapi import SlackEventAdapter

DEPLOYS_CHANNEL_NAME = "#slack_bot_deploys"
JOINS_CHANNEL_ID = "C0762DHUUH1"

GITHUB_API_URL = "https://github.com/OWASP-BLT/BLT"
load_dotenv()


app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(os.environ["SIGNING_SECRET"], "/slack/events", app)
client = WebClient(token=os.environ["SLACK_TOKEN"])
client.chat_postMessage(channel=DEPLOYS_CHANNEL_NAME, text="bot started v1.8 24-05-28 top")


def fetch_github_data(owner, repo):
    prs = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls?state=closed").json()
    issues = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=closed").json()
    comments = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/comments").json()
    return prs, issues, comments


def format_data(prs, issues, comments):
    user_data = {}

    for pr in prs:
        user = pr["user"]["login"]
        if user not in user_data:
            user_data[user] = {"prs": 0, "issues": 0, "comments": 0}
        user_data[user]["prs"] += 1

    for issue in issues:
        user = issue["user"]["login"]
        if user not in user_data:
            user_data[user] = {"prs": 0, "issues": 0, "comments": 0}
        user_data[user]["issues"] += 1

    for comment in comments:
        user = comment["user"]["login"]
        if user not in user_data:
            user_data[user] = {"prs": 0, "issues": 0, "comments": 0}
        user_data[user]["comments"] += 1

    table = (
        "User | PRs Merged | Issues Resolved | Comments\n"
        " ---- | ---------- | --------------- | --------\n"
    )
    for user, counts in user_data.items():
        table += f"{user} | {counts['prs']} | {counts['issues']} | {counts['comments']}\n"

    return table


@app.route("/contributors", methods=["POST"])
def contributors():
    owner = "OWASP-BLT"
    repo = "BLT"

    prs, issues, comments = fetch_github_data(owner, repo)

    return jsonify(
        {
            "response_type": "in_channel",
            "text": format_data(prs, issues, comments) or "No data available",
        }
    )
