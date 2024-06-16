import os
import sys

from dotenv import load_dotenv

project_folder = os.path.expanduser("/home/DonnieBLT/BLT-Lettuce")
load_dotenv(os.path.join(project_folder, ".env"))
SIGNING_SECRET = os.getenv("SIGNING_SECRET")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
# Ensure the project directory is in the Python path
project_home = "/home/DonnieBLT/BLT-Lettuce"
if project_home not in sys.path:
    sys.path.insert(0, project_home)
# Define the WSGI application object
