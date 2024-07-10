import logging
import re
import time
import dateparser
from datetime import datetime, timedelta
from github import Github
from github import Auth
import requests
from dotenv import dotenv_values
from slack_sdk.web.async_client import AsyncSlackResponse
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command
from typing import Any, Sequence
from slack_sdk.models.blocks import Block
from slack_sdk.models.attachments import Attachment

secrets = dotenv_values(".secrets")

SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]

reminder_pattern = re.compile(r"\[(.*?)\]\s+\[(.+?)\]\s+\[(.+?)\]")


class ReminderPlugin(MachineBasePlugin):
    def parse_command(self, command_text):
        match = reminder_pattern.match(command_text)
        if match:
            channel_name, message, when = match.groups()
            if "every" in when:
                when = when.lstrip("every ")
                every = True
            else:
                every = False
            return channel_name, message, when, every
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

    def convert_to_datetime(self, when):
        try:
            date = dateparser.parse(when)
            return date
        except ValueError:
            return None

    async def say_scheduled(
        self,
        when,
        channel,
        text,
        attachments: Sequence[Attachment] | Sequence[dict[str, Any]] | None = None,
        blocks: Sequence[Block] | Sequence[dict[str, Any]] | None = None,
        thread_ts: str | None = None,
        **kwargs: Any,
    ) -> AsyncSlackResponse:
        return await self._client.send_scheduled(
            when,
            channel,
            text=text,
            attachments=attachments,
            blocks=blocks,
            thread_ts=thread_ts,
            **kwargs,
        )

    @command("/setreminder")
    async def reminder(self, command):
        try:
            self_channel = command._cmd_payload["channel_id"]
            text = command.text.strip()
            logging.info(f"Received command text: {text}")
            channel_name, message, when, every = self.parse_command(text)
            channel_id = self.get_channel_id(channel_name)
            if not channel_id or not message or not when:
                await self.web_client.chat_postMessage(
                    channel=self_channel,
                    text="Invalid command format. Please use [channel_id] [what] [when].",
                )
                logging.error("Invalid command format")
                return

            post_at = self.convert_to_datetime(when)
            if not post_at:
                await self.web_client.chat_postMessage(
                    channel=self_channel, text=f"Invalid time format for 'when': {when}."
                )
                logging.error(f"Invalid time format for 'when': {when}")
                return

            response = await self.say_scheduled(post_at, channel_id, message)
            print(response)
            if response["ok"]:
                await self.web_client.chat_postMessage(
                    channel=self_channel,
                    text=(
                        f"Message scheduled successfully for"
                        f" {post_at.strftime('%Y-%m-%d %H:%M:%S')} in channel {channel_id}."
                    ),
                )
                logging.info(
                    f"Message scheduled successfully for"
                    f" {post_at.strftime('%Y-%m-%d %H:%M:%S')} in channel {channel_id}."
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
