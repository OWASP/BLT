from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from machine.clients.slack import SlackClient
from machine.storage import PluginStorage
from machine.utils.collections import CaseInsensitiveDict

from sammich.plugins.project import ProjectPlugin


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
def project_plugin(mock_slack_client, mock_settings, mock_storage):
    """Fixture to create a ProjectPlugin instance with mocked dependencies."""
    plugin = ProjectPlugin(mock_slack_client, mock_settings, mock_storage)
    plugin.project_data = {
        "project1": ["Task 1", "Task 2", "Task 3"],
        "project2": ["Task A", "Task B"],
    }
    with patch.object(ProjectPlugin, "web_client", new_callable=PropertyMock) as mock_web_client:
        mock_web_client.return_value.chat_postMessage = AsyncMock()
        plugin._web_client = mock_web_client
        yield plugin


@pytest.fixture
def mock_command():
    """Fixture to mock a command object."""
    cmd = MagicMock()
    cmd.text.strip.return_value.lower.return_value = "project1"
    cmd._cmd_payload = {"channel_id": "test_channel"}
    cmd.say = AsyncMock()
    return cmd


@pytest.fixture
def mock_action():
    """Fixture to mock an action object."""
    action = MagicMock()
    action.payload.actions[0].selected_option.value = "project1"
    action.say = AsyncMock()
    return action


@pytest.mark.asyncio
async def test_project_command(project_plugin, mock_command):
    """Test the project command with a valid project."""
    await project_plugin.project(mock_command)
    mock_command.say.assert_awaited_once_with(
        "Hello, here the information about 'project1':\nTask 1\nTask 2\nTask 3"
    )


@pytest.mark.asyncio
async def test_project_command_no_project(project_plugin, mock_command):
    """Test the project command with a nonexistent project."""
    mock_command.text.strip.return_value.lower.return_value = "nonexistent"
    await project_plugin.project(mock_command)
    mock_command.say.assert_not_called()
    project_plugin._web_client.return_value.chat_postMessage.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_dropdown_selection(project_plugin, mock_action):
    """Test handling dropdown selection action."""
    await project_plugin.handle_dropdown_selection(mock_action)
    mock_action.say.assert_awaited_once_with(
        "Hello, here is the information about 'project1':\nTask 1\nTask 2\nTask 3"
    )
