from flask import Flask, request,jsonify
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from dotenv import load_dotenv
import logging
import os
import git
from slack_sdk.errors import SlackApiError

load_dotenv()

logging.basicConfig(filename='slack_messages.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], "/slack/events", app)
client = WebClient(token=os.environ['SLACK_TOKEN'])
client.chat_postMessage(channel='#project-blt-lettuce-deploys', text=f"bot started v1.7 top")

# keep for debugging purposes
#@app.before_request
#def log_request():
#    if request.path == '/slack/events' and request.method == 'POST':
#        # Log the request headers and body
#        logging.info(f"Headers: {request.headers}")
#        logging.info(f"Body: {request.get_data(as_text=True)}")
     
@app.route('/update_server', methods=['POST'])
def webhook():
    # check if there is an API key - 
    
    if request.method == 'POST':
        current_directory = os.path.dirname(os.path.abspath(__file__))
        repo = git.Repo(current_directory)
        origin = repo.remotes.origin
        origin.pull()
        latest_commit = repo.head.commit
        latest_commit_message = latest_commit.message.strip()
        client.chat_postMessage(channel='#project-blt-lettuce-deploys', text=f"Deployed the latest version 1.8. Latest commit: {latest_commit_message}")
        return 'OK', 200
    else:
        return 'Error', 400


@slack_events_adapter.on("team_join")
def handle_team_join(event_data):
    user_id = event_data["event"]["user"]["id"]
    # private channel for joins so it does not get noisy
    response = client.chat_postMessage(channel='C06RMMRMGHE', text=f"<@{user_id}> joined the team.")
    if not response["ok"]:
        client.chat_postMessage(channel='#project-blt-lettuce-deploys', text=f"Error sending message: {response['error']}")
        logging.error(f"Error sending message: {response['error']}")

@slack_events_adapter.on("member_joined_channel")
def handle_member_joined_channel(event_data):
    event = event_data["event"]
    user_id = event["user"]
    channel_id = event["channel"]
    # send a message to the user if they joined the #owasp-community channel
    
    client.chat_postMessage(channel=channel_id, text=f"Welcome <@{user_id}> to the <#{channel_id}> channel!")


@slack_events_adapter.on("message")
def handle_message(payload):
    message = payload.get("event", {})

    try:
        response = client.auth_test()
        bot_user_id = response["user_id"]
    except SlackApiError as e:
        bot_user_id = None

    # Check if the message was not sent by the bot itself
    if message.get("user") != bot_user_id:
        if (message.get("subtype") is None and
            not any(keyword in message.get("text", "").lower() for keyword in ["#contribute"]) and
            any(keyword in message.get("text", "").lower() for keyword in ["contribute", "contributing", "contributes"])):
            
            user = message.get("user")
            channel = message.get("channel")
            logging.info(f"detected contribute sending to channel: {channel}")
            response = client.chat_postMessage(channel=channel, text=f"Hello <@{user}>! Please check this channel <#C04DH8HEPTR> for contributing guidelines today!")
            if not response["ok"]:
                client.chat_postMessage(channel='#project-blt-lettuce-deploys', text=f"Error sending message: {response['error']}")
                logging.error(f"Error sending message: {response['error']}")

    if message.get('channel_type') == 'im':
        user = message['user']  # The user ID of the person who sent the message
        text = message.get('text', '')  # The text of the message
        
        try:
            client.chat_postMessage(channel='C06RMMRMGHE', text=f"<@{user}> said {text}")
            # Respond to the direct message
            client.chat_postMessage(channel=user, text=f"Hello <@{user}>, you said: {text}")
        except SlackApiError as e:
            print(f"Error sending response: {e.response['error']}")

