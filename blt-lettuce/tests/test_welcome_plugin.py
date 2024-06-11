import pytest
from unittest.mock import AsyncMock, patch
from src.lettuce.plugins.welcome import WelcomePlugin  # Adjust the import according to your project structure

@pytest.mark.asyncio
async def test_welcome_plugin(mocker):
    mock_client = mocker.Mock()
    mock_settings = mocker.Mock()
    mock_storage = mocker.Mock()

    plugin = WelcomePlugin(
        client=mock_client, settings=mock_settings, storage=mock_storage
    )
    plugin.say = AsyncMock()

    event = {
        'user': {'id': 'U1234567890'}
    }

    # Mock the conversations_open API response using patch
    with patch.object(plugin.web_client, 'conversations_open', AsyncMock(return_value={'channel': {'id': 'D1234567890'}})):
        # Mock the open function to return the content of welcome_message.txt
        welcome_message_content = """
        :tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:

        We're thrilled to have you here! Whether you're new to OWASP or a long-time contributor, this Slack workspace is the perfect place to connect, collaborate, and stay informed about all things OWASP.

        :small_blue_diamond: *Get Involved:*
        • Check out the *#contribute* channel to find ways to get involved with OWASP projects and initiatives.
        • Explore individual project channels, which are named *#project-name*, to dive into specific projects that interest you.
        • Join our chapter channels, named *#chapter-name*, to connect with local OWASP members in your area.

        :small_blue_diamond: *Stay Updated:*
        • Visit *#newsroom* for the latest updates and announcements.
        • Follow *#external-activities* for news about OWASP's engagement with the wider security community.

        :small_blue_diamond: *Connect and Learn:*
        • *#jobs*: Looking for new opportunities? Check out the latest job postings here.
        • *#leaders*: Connect with OWASP leaders and stay informed about leadership activities.
        • *#project-committee*: Engage with the committee overseeing OWASP projects.
        • *#gsoc*: Stay updated on Google Summer of Code initiatives.
        • *#github-admins*: Get support and discuss issues related to OWASP's GitHub repositories.
        • *#learning*: Share and find resources to expand your knowledge in the field of application security.

        We're excited to see the amazing contributions you'll make. If you have any questions or need assistance, don't hesitate to ask. Let's work together to make software security visible and improve the security of the software we all rely on.

        Welcome aboard! :rocket:
        """

        with patch('builtins.open', mocker.mock_open(read_data=welcome_message_content)):
            await plugin.welcome(event)

        expected_message = welcome_message_content.strip().format(user_id='U1234567890')
        plugin.say.assert_called_once_with(
            channel='D1234567890',
            text='Welcome to the OWASP Slack Community!',
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": expected_message
                    }
                }
            ]
        )
