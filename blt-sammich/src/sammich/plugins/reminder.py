import datetime
import logging
import re
import time

import requests
from dotenv import dotenv_values
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

secrets = dotenv_values(".secrets")

SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]


class ReminderPlugin(MachineBasePlugin):
    def parse_command(self, command_text):
        pattern = re.compile(r"\[(.*?)\]\s+\[(.+?)\]\s+\[(.+?)\]")
        match = pattern.match(command_text)
        if match:
            channel_name, message, when = match.groups()
            return channel_name, message, when
        return None, None, None

    def get_channel_id(self, channel_name):
        # Use Slack API to get the channel ID from the channel name
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        }
        response = requests.get("https://slack.com/api/conversations.list", headers=headers)
        channels = response.json().get("channels", [])
        for channel in channels:
            if channel["name"] == channel_name.lstrip("#"):
                return channel["id"]
        return None

    def convert_to_timestamp(self, when):
        try:
            future_time_str = when
            future_time = datetime.datetime.strptime(future_time_str, "%d/%m/%Y %I:%M %p")
            future_timestamp = int(future_time.timestamp())

            return future_timestamp
        except ValueError:
            return None

    def schedule_message(self, channel_id, text, post_at):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        }
        data = {
            "channel": channel_id,
            "text": text,
            "post_at": post_at,
        }
        response = requests.post(
            "https://slack.com/api/chat.scheduleMessage", headers=headers, json=data
        )
        return response.json()

    @command("/setreminder")
    async def reminder(self, command):
        try:
            self_channel = command._cmd_payload["channel_id"]
            text = command.text.strip()
            logging.info(f"Received command text: {text}")
            channel_name, message, when = self.parse_command(text)
            channel_id = self.get_channel_id(channel_name)
            if not channel_id or not message or not when:
                await self.web_client.chat_postMessage(
                    channel=self_channel,
                    text="Invalid command format. Please use [channel_id] [what] [when].",
                )
                logging.error("Invalid command format")
                return

            post_at = self.convert_to_timestamp(when)
            if not post_at:
                await self.web_client.chat_postMessage(
                    channel=self_channel, text=f"Invalid time format for 'when': {when}."
                )
                logging.error(f"Invalid time format for 'when': {when}")
                return

            response = self.schedule_message(channel_id, message, post_at)
            if response.get("ok"):
                await self.web_client.chat_postMessage(
                    channel=self_channel,
                    text=(
                        f"Message scheduled successfully for"
                        f"{time.ctime(post_at)} in channel {channel_id}."
                    ),
                )
                logging.info(
                    f"Message scheduled successfully for"
                    f"{time.ctime(post_at)} in channel {channel_id}."
                )
            else:
                await self.web_client.chat_postMessage(
                    channel=self_channel, text=f"Failed to schedule message: {response['error']}"
                )
                logging.error(f"Failed to schedule message: {response['error']}")
        except Exception as e:
            logging.error(f"Exception in command handling: {str(e)}")
            await self.web_client.chat_postMessage(
                channel=self_channel, text="An error occurred while processing the command."
            )


# Initialize logging
logging.basicConfig(level=logging.INFO)
