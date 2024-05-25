from flask import Flask, request,jsonify
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from dotenv import load_dotenv
import logging
import os
import git
from slack_sdk.errors import SlackApiError
from slack_bolt import App
import sqlite3

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

@app.command("/setcrypto")
def set_crypto_command(ack, say, command):
    ack()
    user_id = command["user_id"]
    crypto_name, address = command["text"].split()

    # Connect to the SQLite database
    conn = sqlite3.connect('crypto_addresses.db')
    cursor = conn.cursor()

    # Insert the user's data into the database
    cursor.execute("INSERT INTO addresses (user_id, crypto_name, address) VALUES (?, ?, ?)", (user_id, crypto_name, address))
    conn.commit()
    conn.close()

    say(f"Your cryptocurrency address for {crypto_name} has been saved.")

    return jsonify({
        "response_type": "in_channel",
        "text": f"Your cryptocurrency address for {crypto_name} has been saved."
    })

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
            if message.get("user") != bot_user_id:
                client.chat_postMessage(channel='C06RMMRMGHE', text=f"<@{user}> said {text}")
            # Respond to the direct message
            client.chat_postMessage(channel=user, text=f"Hello <@{user}>, you said: {text}")
        except SlackApiError as e:
            print(f"Error sending response: {e.response['error']}")

@app.route('/repo', methods=['POST'])
def list_repo():
    data = request.form
    command = data.get('command')
    text = data.get('text')
    user_name = data.get('user_name')
    tech_name = text.strip().lower()
    response_message = ""
        
    if tech_name == 'django':
        response_message = f"Hello {user_name}, You can implement your '{tech_name}' knowledge here:
        (https://github.com/OWASP-BLT/BLT)"
    elif tech_name == 'python':
         response_message = f"Hello {user_name}, You can implement your '{tech_name}' knowledge here:
        (https://github.com/OWASP-BLT/BLT)
        https://github.com/OWASP-BLT/BLT-Flutter) 
        (https://github.com/OWASP-BLT/BLT-Lettuce)"
    elif tech_name == 'flutter' or tech_name == 'dart':
        response_message = f"Hello {user_name}, You can implement your '{tech_name}' knowledge here: 
        (https://github.com/OWASP-BLT/BLT-Flutter) 
        (https://github.com/OWASP-BLT/BLT-Lettuce)"
    elif tech_name == 'blockchain'or tech_name == 'cryptography':
        response_message = f"Hello {user_name}, You can implement your '{tech_name}' knowledge here:
        (https://github.com/OWASP-BLT/BLT-Bacon)"
    elif tech_name == 'javascript':
        response_message = f"Hello {user_name}, You can implement your '{tech_name}' knowledge here:
        (https://github.com/OWASP-BLT/BLT-Action)  
        (https://github.com/OWASP-BLT/BLT-Extension)  
        (https://github.com/OWASP-BLT/BLT)"
    elif tech_name == 'html' or tech_name == 'css':
        response_message = f"Hello {user_name}, You can implement your '{tech_name}' knowledge here:
        (https://github.com/OWASP-BLT/BLT-Extension)  
        (https://github.com/OWASP-BLT/BLT)"
    else:
        response_message = f"Hello {user_name}, the technology '{tech_name}' is not recognized. Please try again."
    return jsonify({
        'response_type': 'in_channel',
        'text': response_message,
    })
