from flask import Flask, request,jsonify
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from dotenv import load_dotenv
import logging
import os

load_dotenv()  # Load environment variables from .env file

logging.basicConfig(filename='slack_messages.log', level=logging.INFO)
app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], "/slack/events", app)
client = WebClient(token=os.environ['SLACK_TOKEN'])

@slack_events_adapter.on("member_joined_channel")
def handle_member_joined_channel(event_data):
    event = event_data["event"]
    user_id = event["user"]
    channel_id = event["channel"]
    client.chat_postMessage(channel='#trying_bot', text=f"Welcome <@{user_id}> to the channel!")


@slack_events_adapter.on("message")
def handle_message(payload):
    message = payload.get("event",{})
    if message.get("subtype") is None and not any(keyword in message.get("text", "").lower() for keyword in ["#contribute"]) and any(keyword in message.get("text", "").lower() for keyword in ["contribute", "contributing", "contributes"]):
        user = message.get("user")
        channel = message.get("channel")
        channel_id="C04DH8HEPTR"
        client.chat_postMessage(channel='#trying_bot', text=f"Hello <@{user}>! please check this channel <#{channel_id}>")

@app.route("/slack/events", methods=["POST"])
def slack_events():
    # Verify the request came from Slack
    if request.headers.get('X-Slack-Signature') and request.headers.get('X-Slack-Request-Timestamp'):
        slack_events_adapter.handle(request.data.decode('utf-8'), request.headers.get('X-Slack-Signature'), request.headers.get('X-Slack-Request-Timestamp'))
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"error": "invalid request"}), 400

if __name__ == "__main__":
    app.run(port=3000)
