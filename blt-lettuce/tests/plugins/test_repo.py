from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from machine.clients.slack import SlackClient
from machine.storage import PluginStorage
from machine.utils.collections import CaseInsensitiveDict

from lettuce.plugins.repo import RepoPlugin


@pytest.fixture
def mock_slack_client():
    """Fixture to mock the SlackClient."""
    return MagicMock(SlackClient)


@pytest.fixture
def mock_settings():
    """Fixture to mock settings."""
    return CaseInsensitiveDict()


@pytest.fixture
def mock_storage():
    """Fixture to mock PluginStorage."""
    return MagicMock(PluginStorage)


@pytest.fixture
def repo_plugin(mock_slack_client, mock_settings, mock_storage):
    """Fixture to create a RepoPlugin instance with mocked dependencies."""
    plugin = RepoPlugin(mock_slack_client, mock_settings, mock_storage)
    plugin.repo_data = {
        "python": ["https://github.com/example/python-repo"],
        "java": ["https://github.com/example/java-repo"],
    }
    with patch.object(RepoPlugin, "web_client", new_callable=PropertyMock) as mock_web_client:
        mock_web_client.return_value.chat_postMessage = AsyncMock()
        plugin._web_client = mock_web_client
        yield plugin


@pytest.fixture
def mock_command():
    """Fixture to mock a command object."""
    cmd = MagicMock()
    cmd.text.strip.return_value.lower.return_value = "python"
    cmd._cmd_payload = {"channel_id": "test_channel"}
    cmd.say = AsyncMock()
    return cmd


@pytest.fixture
def mock_action():
    """Fixture to mock an action object."""
    action = MagicMock()
    action.payload.actions[0].value = "python"
    action.say = AsyncMock()
    return action


@pytest.mark.asyncio
async def test_repo_command(repo_plugin, mock_command):
    """Test the repo command with a valid repository."""
    await repo_plugin.repo(mock_command)
    mock_command.say.assert_awaited_once_with(
        "Hello, you can implement your 'python' knowledge here:\nhttps://github.com/example/python-repo"
    )


@pytest.mark.asyncio
async def test_repo_command_no_repo(repo_plugin, mock_command):
    """Test the repo command with a nonexistent repository."""
    mock_command.text.strip.return_value.lower.return_value = "nonexistent"
    await repo_plugin.repo(mock_command)
    mock_command.say.assert_not_called()
    repo_plugin._web_client.return_value.chat_postMessage.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_button_click(repo_plugin, mock_action):
    """Test handling button click action."""
    await repo_plugin.handle_button_click(mock_action)
    mock_action.say.assert_awaited_once_with(
        "Hello, you can implement your 'python' knowledge here:\nhttps://github.com/example/python-repo"
    )
