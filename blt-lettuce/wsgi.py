import os
import sys
import logging
from flask import Flask, request, jsonify
from slack_sdk.web.async_client import AsyncWebClient
from slackeventsapi import SlackEventAdapter
from machine.clients.slack_request_url import SlackClientRequestURL
from machine.clients.slack import SlackClient
from machine.plugins.command import Command
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import subprocess
import json

# Function to import settings module dynamically
def import_settings(settings_module_path):
    module_name = os.path.splitext(os.path.basename(settings_module_path))[0]
    module_dir = os.path.dirname(settings_module_path)

    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    try:
        settings = __import__(module_name)
        return settings, True
    except ImportError as e:
        print(f"Error importing {settings_module_path}: {e}")
        return None, False

# Ensure the project directory is in the Python path
project_home = '/home/DonnieBLT/BLT-Lettuce'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Get the settings module from environment variable or default to local_settings.py
settings_module_path = os.environ.get("SM_SETTINGS_MODULE", "/home/DonnieBLT/BLT-Lettuce/src/local_settings.py")
settings, found_local_settings = import_settings(settings_module_path)

# Add debugging to ensure the correct path and loading
print(f"Settings module path: {settings_module_path}")
print(f"Settings loaded: {settings}")
print(f"SLACK_BOT_TOKEN from settings: {getattr(settings, 'SLACK_BOT_TOKEN', None)}")
print(f"SLACK_SIGNING_TOKEN from settings: {getattr(settings, 'SLACK_SIGNING_TOKEN', None)}")

if not found_local_settings:
    raise ImportError(f"Settings module {settings_module_path} not found")

if not getattr(settings, 'SLACK_SIGNING_TOKEN', None):
    raise ValueError("SLACK_SIGNING_TOKEN is required but not found in settings")

# Load environment variables
load_dotenv()

# Setting up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Ensure we have a console handler for the logger
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.debug("Loading wsgi.py file")
logger.debug(f"SLACK_BOT_TOKEN: {getattr(settings, 'SLACK_BOT_TOKEN', None)}")
logger.debug(f"SLACK_SIGNING_TOKEN: {getattr(settings, 'SLACK_SIGNING_TOKEN', None)}")

# Create the Flask app
app = Flask(__name__)

# Initialize the Async Slack client
async_slack_client = SlackClientRequestURL(
    AsyncWebClient(token=getattr(settings, 'SLACK_BOT_TOKEN', None)), ZoneInfo("UTC")
)
logger.info("slack_client is %s", async_slack_client)

# Setting up the SlackEventAdapter
slack_events_adapter = SlackEventAdapter(
    getattr(settings, 'SLACK_SIGNING_TOKEN', None), "/slack/events", app
)
logger.info("slack_events_adapter is %s", slack_events_adapter)

# Logging incoming requests for debugging
@app.before_request
def log_request_info():
    logger.debug('Headers: %s', request.headers)
    logger.debug('Body: %s', request.get_data())

# Handle Slack events
@app.route('/slack/events', methods=['POST'])
def slack_events():
    try:
        event_data = json.loads(request.data.decode('utf-8'))
        return slack_events_adapter.server.event(request)
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400

# Handle Slack slash commands and route to slack-machine
@app.route('/slack/commands', methods=['POST'])
def slack_commands():
    if request.content_type == 'application/x-www-form-urlencoded':
        form_data = request.form.to_dict()
        logger.debug(f"Form Data: {form_data}")

        # Initialize the Slack client properly
        try:
            slack_client = SlackClient(
                client=AsyncWebClient(token=getattr(settings, 'SLACK_BOT_TOKEN', None)),
                tz=ZoneInfo("UTC")
            )
            command = Command(slack_client, form_data)

            # Assuming a `plugins` object that handles command routing in your slack-machine setup
            from machine.plugins.base import MachineBasePlugin

            # Find the appropriate plugin to handle the command
            response = None
            for plugin in MachineBasePlugin.__subclasses__():
                if hasattr(plugin, "handle_command"):
                    response = plugin().handle_command(command)
                    if response:
                        break

            if response:
                response_message = {
                    "response_type": "in_channel",
                    "text": f"Command {form_data['command']} received and processed: {response}"
                }
            else:
                response_message = {
                    "response_type": "ephemeral",
                    "text": f"Command {form_data['command']} could not be processed."
                }

        except ImportError as e:
            logger.error(f"ImportError: {e}")
            return jsonify({'error': 'Failed to import Slack module'}), 500
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return jsonify({'error': f"Error processing command: {e}"}), 500

        # Respond to the command
        return jsonify(response_message)
    else:
        logger.error(f"Unsupported Content-Type: {request.content_type}")
        return jsonify({'error': 'Unsupported Content-Type'}), 400

# Adding event handlers for the SlackEventAdapter
@slack_events_adapter.on("team_join")
async def handle_team_join(event_data):
    event = event_data["event"]
    await async_slack_client._on_team_join(event)

@slack_events_adapter.on("user_change")
async def handle_user_change(event_data):
    event = event_data["event"]
    await async_slack_client._on_user_change(event)

@slack_events_adapter.on("channel_created")
async def handle_channel_created(event_data):
    event = event_data["event"]
    await async_slack_client._on_channel_created(event)

@slack_events_adapter.on("channel_deleted")
async def handle_channel_deleted(event_data):
    event = event_data["event"]
    await async_slack_client._on_channel_deleted(event)

@slack_events_adapter.on("channel_rename")
@slack_events_adapter.on("group_rename")
@slack_events_adapter.on("channel_archive")
@slack_events_adapter.on("group_archive")
@slack_events_adapter.on("channel_unarchive")
@slack_events_adapter.on("group_unarchive")
async def handle_channel_updated(event_data):
    event = event_data["event"]
    await async_slack_client._on_channel_updated(event)

@slack_events_adapter.on("channel_id_changed")
async def handle_channel_id_changed(event_data):
    event = event_data["event"]
    await async_slack_client._on_channel_id_changed(event)

@slack_events_adapter.on("member_joined_channel")
async def handle_member_joined_channel(event_data):
    event = event_data["event"]
    await async_slack_client._on_member_joined_channel(event)

# Define a simple route for the main Flask app
@app.route('/')
def hello_main():
    return "Hello from the main Flask app!"

# If you need to start any background processes like slack-machine, you can do so here.
# Example (adjust the command to suit your environment):
venv_activate = os.path.expanduser('/home/DonnieBLT/.cache/pypoetry/virtualenvs/lettuce-blt-As9VAFFe-py3.10/bin/activate')

if not os.path.exists(venv_activate):
    raise FileNotFoundError(f"Virtual environment activation script not found: {venv_activate}")

command = f"source {venv_activate} && nohup slack-machine &"
try:
    subprocess.run(command, shell=True, check=True, executable="/bin/bash")
except subprocess.CalledProcessError as e:
    print(f"Error starting slack-machine: {e}")
except FileNotFoundError as e:
    print(f"slack-machine executable not found: {e}")
print('started')

# Define the WSGI application object
application = app
