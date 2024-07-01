import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import git
from cachetools import TTLCache
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from openai import OpenAI
from slack import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

DEPLOYS_CHANNEL_NAME = "#project-blt-lettuce-deploys"
JOINS_CHANNEL_ID = "C06RMMRMGHE"
CONTRIBUTE_ID = "C04DH8HEPTR"

load_dotenv()

logging.basicConfig(
    filename="slack_messages.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(os.environ["SIGNING_SECRET"], "/slack/events", app)
client = WebClient(token=os.environ["SLACK_TOKEN"])
client.chat_postMessage(channel=DEPLOYS_CHANNEL_NAME, text="bot started v1.9 240611-1 top")

template = """
    You're a Software Engineer (Mentor) at OWASP,
    Your job is to provide help to contributors with a short message.
    Contributor' Question :{Doubt}
"""


openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

cache = TTLCache(maxsize=100, ttl=86400)


@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json

    # Respond to Slack's URL verification challenge
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    # Handle other event types here
    event = data.get("event", {})
    handle_message(event)

    return "Event received", 200


# keep for debugging purposes
# @app.before_request
# def log_request():
#    if request.path == '/slack/events' and request.method == 'POST':
#        # Log the request headers and body
#        logging.info(f"Headers: {request.headers}")
#        logging.info(f"Body: {request.get_data(as_text=True)}")


# Determine the root directory (assumes the script is run from the root folder)
root_dir = Path(__file__).resolve().parent


@app.route("/update_server", methods=["POST"])
def webhook():
    if request.method == "POST":
        current_directory = os.path.dirname(os.path.abspath(__file__))
        repo = git.Repo(current_directory)
        origin = repo.remotes.origin
        origin.pull()
        latest_commit_message = repo.head.commit.message.strip()
        client.chat_postMessage(
            channel=DEPLOYS_CHANNEL_NAME,
            text=f"Deployed the latest version 1.8. Latest commit: {latest_commit_message}",
        )
        return "OK", 200

    return "Error", 400


@slack_events_adapter.on("team_join")
def handle_team_join(event_data):
    user_id = event_data["event"]["user"]["id"]

    # Post a message in the private joins channel
    response = client.chat_postMessage(
        channel=JOINS_CHANNEL_ID, text=f"<@{user_id}> joined the team."
    )

    if not response["ok"]:
        client.chat_postMessage(
            channel=DEPLOYS_CHANNEL_NAME,
            text=f"Error sending message: {response['error']}",
        )
        logging.error(f"Error sending message: {response['error']}")

    try:
        response = client.conversations_open(users=[user_id])
        dm_channel_id = response["channel"]["id"]

        with open("welcome_message.txt", "r", encoding="utf-8") as file:
            welcome_message_template = file.read()

        welcome_message = welcome_message_template.format(user_id=user_id)
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": welcome_message.strip()}}]

        client.chat_postMessage(
            channel=dm_channel_id, text="Welcome to the OWASP Slack Community!", blocks=blocks
        )
    except Exception as e:
        logging.error(f"Error sending welcome message: {e}")


@slack_events_adapter.on("message")
def handle_message(payload):
    message = payload.get("event", {})
    try:
        response = client.auth_test()
        bot_user_id = response["user_id"]
    except SlackApiError:
        bot_user_id = None
    # Check if the message was not sent by the bot itself
    if message.get("user") != bot_user_id:
        if (
            message.get("subtype") is None
            and not any(keyword in message.get("text", "").lower() for keyword in ["#contribute"])
            and any(
                keyword in message.get("text", "").lower()
                for keyword in ("contribute", "contributing", "contributes")
            )
        ):
            user = message.get("user")
            channel = message.get("channel")
            response = client.chat_postMessage(
                channel=channel,
                text=(
                    f"Hello <@{user}>! Please check this channel "
                    f"<#{CONTRIBUTE_ID}> for contributing guidelines today!"
                ),
            )
            if not response["ok"]:
                client.chat_postMessage(
                    channel=DEPLOYS_CHANNEL_NAME,
                    text=f"Error sending message: {response['error']}",
                )
                logging.error(f"Error sending message: {response['error']}")
    # if message.get("channel_type") == "im":
    #     user = message["user"]  # The user ID of the person who sent the message
    #     text = message.get("text", "")  # The text of the message
    #     try:
    #         if message.get("user") != bot_user_id:
    #             client.chat_postMessage(channel=JOINS_CHANNEL_ID, text=f"<@{user}> said {text}")
    #         # Respond to the direct message
    #         client.chat_postMessage(channel=user, text=f"Hello <@{user}>, you said: {text}")
    #     except SlackApiError as e:
    #         print(f"Error sending response: {e.response['error']}")


@slack_events_adapter.on("message")
def gpt_bot(payload):
    token_limit = 1000
    token_per_prompt = 100
    user = "D078YQ93TSL"
    message = payload.get("event", {})

    if message.get("channel_type") == "im":
        doubt = message.get("text", "")
        prompt = template.format(doubt=doubt)

        today = datetime.now(timezone.utc).date()
        rate_limit_key = f"global_daily_request_{today}"
        total_token_used = cache.get(rate_limit_key, 0)

        if len(doubt) > 50:
            client.chat_postMessage(channel=user, text="Please enter less than 50 characters")
            return

        if total_token_used + token_per_prompt > token_limit:
            client.chat_postMessage(channel=user, text="Exceeds Token Limit")
            return

        try:
            response = openai_client.Completion.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-3.5-turbo-0125",
                max_tokens=20,
            )
            answer = response.choices[0].message.content
        except Exception as e:
            logging.error(f"OpenAI API request failed: {e}")
            client.chat_postMessage(
                channel=user, text="An error occurred while processing your request."
            )
            return

        try:
            client.chat_postMessage(channel=user, text=f"{answer}")
            cache[rate_limit_key] = total_token_used + token_per_prompt

            # Log the user's question and GPT's answer
            logging.info(f"User's Question: {doubt}")
            logging.info(f"GPT's Answer: {answer}")
        except SlackApiError as e:
            logging.error(f"Error sending message to Slack: {e.response['error']}")
