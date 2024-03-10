from flask import Flask, request
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from dotenv import load_dotenv
import os


load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], "/slack/events", app)
client = WebClient(token=os.environ['SLACK_TOKEN'])

@slack_events_adapter.on("team_join")
def handle_team_join(event_data):
    user_id = event_data["event"]["user"]["id"]
    client.chat_postMessage(channel='#trying_bot', text=f"Welcome <@{user_id}> to the team!")

@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    if message.get("subtype") is None and "contribut" in message.get("text", ""):
        user = message["user"]
        channel = message["channel"]
        client.chat_postMessage(channel='#trying_bot', text=f"Hello <@{user}>! please go through our readme ")

if __name__ == "__main__":
    app.run(port=3000)