from flask import Flask, request,jsonify
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from dotenv import load_dotenv
import logging
import os
import git
from slack_sdk.errors import SlackApiError
#test
load_dotenv()

logging.basicConfig(filename='slack_messages.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], "/slack/events", app)
client = WebClient(token=os.environ['SLACK_TOKEN'])
client.chat_postMessage(channel='#project-blt-lettuce-deploys', text=f"bot started v1.7 top")
 
@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method == 'POST':
        current_directory = os.path.dirname(os.path.abspath(__file__))
        client.chat_postMessage(channel='#project-blt-lettuce-deploys', text=f"about to deploy {current_directory}")

        repo = git.Repo(current_directory)
        origin = repo.remotes.origin
        origin.pull()

        latest_commit = repo.head.commit
        latest_commit_message = latest_commit.message.strip()

        client.chat_postMessage(channel='#project-blt-lettuce-deploys', text=f"Deployed the latest version 1.8. Latest commit: {latest_commit_message}")
        return 'Updated bot successfully', 200
    else:
        return 'Wrong event type', 400


@slack_events_adapter.on("team_join")
def handle_team_join(event_data):
    user_id = event_data["event"]["user"]["id"]
    response = client.chat_postMessage(channel='#trying_bot', text=f"<@{user_id}> joined the team.")
    if not response["ok"]:
        logging.error(f"Error sending message: {response['error']}")

@slack_events_adapter.on("member_joined_channel")
def handle_member_joined_channel(event_data):
    event = event_data["event"]
    user_id = event["user"]
    channel_id = event["channel"]
    client.chat_postMessage(channel=channel_id, text=f"Welcome <@{user_id}> to the <#{channel_id}> channel!")


@slack_events_adapter.on("message")
def handle_message(payload):
    message = payload.get("event", {})

    try:
        response = client.auth_test()
        bot_user_id = response["user_id"]
        print("Your bot's user ID is:", bot_user_id)
        print("The message is:", message)
    except SlackApiError as e:
        bot_user_id = None
        print(f"Error fetching bot user ID: {e}")

    # Check if the message was not sent by the bot itself
    if message.get("user") != bot_user_id:
        if (message.get("subtype") is None and
            not any(keyword in message.get("text", "").lower() for keyword in ["#contribute"]) and
            any(keyword in message.get("text", "").lower() for keyword in ["contribute", "contributing", "contributes"])):
            
            user = message.get("user")
            channel = message.get("channel")
            logging.info(f"detected contribute sending to channel: {channel}")
            response = client.chat_postMessage(channel=channel, text=f"Hello <@{user}>! Please check this channel <#C04DH8HEPTR> for contributing guidelines!")
            if not response["ok"]:
                logging.error(f"Error sending message: {response['error']}")


# @app.route("/slack/events", methods=["POST"])
# def slack_events():
#     logging.info('/slack/events was called!!!!!!!!!!')
#     # Verify the request came from Slack
#     print('/slack/events was called')
#     print(request)
#     if request.headers.get('X-Slack-Signature') and request.headers.get('X-Slack-Request-Timestamp'):
#         print("slack data:")
#         print(request)
#         slack_events_adapter.handle(request.data.decode('utf-8'), request.headers.get('X-Slack-Signature'), request.headers.get('X-Slack-Request-Timestamp'))
       
#         return jsonify({"status": "ok"}), 200
#     else:
#         return jsonify({"error": "invalid request"}), 400

#if __name__ == "__main__":
#    client.chat_postMessage(channel='#project-blt-lettuce-deploys', text=f"bot started v1.7")
#    print('bot has started')
#    app.run(port=3000)
