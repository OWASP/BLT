import pytest
from unittest.mock import AsyncMock, patch
from lettuce.plugins.welcome.welcome import WelcomePlugin

@pytest.mark.asyncio
async def test_welcome_plugin(mocker):
    mock_client = mocker.Mock()
    mock_settings = mocker.Mock()
    mock_storage = mocker.Mock()

    welcome_message_content = "Hello, <@{user_id}>! Welcome!"

    plugin = WelcomePlugin(client=mock_client, settings=mock_settings, storage=mock_storage)
    with patch.object(plugin, 'welcome_message_template', welcome_message_content):
        plugin.say = AsyncMock()

        event = {
            'user': {'id': 'U1234567890'}
        }

        # Mock the conversations_open API response using patch
        with patch.object(plugin.web_client, 'conversations_open', AsyncMock(return_value={'channel': {'id': 'D1234567890'}})):
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
