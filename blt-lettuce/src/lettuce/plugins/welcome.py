"""Welcome command plugin for BLT-Lettuce Slack bot.

This module implements the /welcome command that sends a welcome
message to users when they join or when they request the welcome info.
"""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def handle_welcome_command(ack, body, client: WebClient) -> None:
    """Handle the /welcome slash command in Slack.
    
    Args:
        ack: Slack command acknowledgment callback
        body: The command request body from Slack
        client: Slack WebClient instance for API calls
    
    Raises:
        SlackApiError: If there's an error sending the message to Slack
    """
    ack()  # Acknowledge the command was received
    
    user_id = body['user_id']
    channel_id = body['channel_id']
    
    welcome_message = {
        "type": "mrkdwn",
        "text": (
            ":wave: *Welcome to BLT!* :wave:\n\n"
            "We're excited to have you here! Here are some things to get started:\n\n"
            "• Check out our <https://github.com/OWASP-BLT|GitHub repository> for more info\n"
            "• Read our contribution guidelines in #contribute\n"
            "• Feel free to ask questions in #general\n"
            "• Join our community and have fun reporting security bugs!\n\n"
            "Questions? Just ask! We're here to help. :smile:"
        )
    }
    
    try:
        client.chat_postMessage(
            channel=channel_id,
            blocks=[
                {
                    "type": "section",
                    "text": welcome_message
                }
            ]
        )
    except SlackApiError as e:
        # Log error but don't fail silently
        print(f"Error posting welcome message: {e}")
        raise


def register_welcome_handler(app) -> None:
    """Register the welcome command handler with the Slack app.
    
    Args:
        app: The Slack Bolt app instance
    """
    app.command("/welcome")(handle_welcome_command)
