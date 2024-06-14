import os
import sys
import logging
from flask import Flask
from slack_sdk.web.async_client import AsyncWebClient
from slackeventsapi import SlackEventAdapter
from machine.clients.slack_request_url import SlackClientRequestURL
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import subprocess


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

# Initialize the Slack client
slack_client = SlackClientRequestURL(
    AsyncWebClient(token=getattr(settings, 'SLACK_BOT_TOKEN', None)), ZoneInfo("UTC")
)
logger.info("slack_client is %s", slack_client)

# Setting up the SlackEventAdapter
slack_events_adapter = SlackEventAdapter(
    getattr(settings, 'SLACK_SIGNING_TOKEN', None), "/slack/events", app
)
logger.info("slack_events_adapter is %s", slack_events_adapter)

# Adding event handlers for the SlackEventAdapter
@slack_events_adapter.on("team_join")
async def handle_team_join(event_data):
    event = event_data["event"]
    await slack_client._on_team_join(event)

@slack_events_adapter.on("user_change")
async def handle_user_change(event_data):
    event = event_data["event"]
    await slack_client._on_user_change(event)

@slack_events_adapter.on("channel_created")
async def handle_channel_created(event_data):
    event = event_data["event"]
    await slack_client._on_channel_created(event)

@slack_events_adapter.on("channel_deleted")
async def handle_channel_deleted(event_data):
    event = event_data["event"]
    await slack_client._on_channel_deleted(event)

@slack_events_adapter.on("channel_rename")
@slack_events_adapter.on("group_rename")
@slack_events_adapter.on("channel_archive")
@slack_events_adapter.on("group_archive")
@slack_events_adapter.on("channel_unarchive")
@slack_events_adapter.on("group_unarchive")
async def handle_channel_updated(event_data):
    event = event_data["event"]
    await slack_client._on_channel_updated(event)

@slack_events_adapter.on("channel_id_changed")
async def handle_channel_id_changed(event_data):
    event = event_data["event"]
    await slack_client._on_channel_id_changed(event)

@slack_events_adapter.on("member_joined_channel")
async def handle_member_joined_channel(event_data):
    event = event_data["event"]
    await slack_client._on_member_joined_channel(event)

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
