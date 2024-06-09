import json

import pytest

from src.lettuce.plugins.demo import DemoPlugin
from src.lettuce.plugins.project import ProjectPlugin
from src.lettuce.plugins.repo import RepoPlugin

repo_json_path = "repo.json"
with open(repo_json_path) as f:
    repos_data = json.load(f)

project_json_path = "projects.json"
with open(project_json_path) as f:
    project_data = json.load(f)


@pytest.mark.asyncio
async def test_demo_command(mocker):
    mock_client = mocker.Mock()
    mock_settings = mocker.Mock()
    mock_storage = mocker.Mock()

    plugin = DemoPlugin(
        client=mock_client, settings=mock_settings, storage=mock_storage
    )

    mock_command = mocker.AsyncMock()
    mock_command.text = "/demo"
    mock_command.say = mocker.AsyncMock()

    await plugin.demo(mock_command)

    mock_command.say.assert_called_once_with("This is a demo response!")


@pytest.mark.asyncio
async def test_repo_command(mocker):
    mock_client = mocker.Mock()
    mock_settings = mocker.Mock()
    mock_storage = mocker.Mock()

    plugin = RepoPlugin(
        client=mock_client, settings=mock_settings, storage=mock_storage
    )

    mock_command = mocker.AsyncMock()
    mock_command.say = mocker.AsyncMock()

    for tech_name in repos_data.keys():
        mock_command.text = tech_name
        await plugin.repo(mock_command)

        if tech_name in repos_data:
            repos_list = "\n".join(repos_data[tech_name])
            expected_message = f"Hello, you can implement your '{tech_name}' knowledge here:\n{repos_list}"
        else:
            expected_message = f"Hello , the technology '{tech_name}' is not recognized. Please try again."

        mock_command.say.assert_called_once_with(expected_message)
        mock_command.reset_mock()


@pytest.mark.asyncio
async def test_wrong_repo_command(mocker):
    mock_client = mocker.Mock()
    mock_settings = mocker.Mock()
    mock_storage = mocker.Mock()

    plugin = RepoPlugin(
        client=mock_client, settings=mock_settings, storage=mock_storage
    )

    mock_command = mocker.AsyncMock()
    mock_command.text = "xyz"
    mock_command.say = mocker.AsyncMock()

    await plugin.repo(mock_command)

    mock_command.say.assert_called_once_with(
        "Hello , the technology 'xyz' is not recognized. Please try again."
    )


@pytest.mark.asyncio
async def test_wrong_project_command(mocker):
    mock_client = mocker.Mock()
    mock_settings = mocker.Mock()
    mock_storage = mocker.Mock()

    plugin = ProjectPlugin(
        client=mock_client, settings=mock_settings, storage=mock_storage
    )

    mock_command = mocker.AsyncMock()
    mock_command.text = "xyx"
    mock_command.say = mocker.AsyncMock()

    await plugin.project(mock_command)

    mock_command.say.assert_called_once_with(
        "Hello , the project 'xyx' is not recognized. Please try different query."
    )


@pytest.mark.asyncio
async def test_project_command(mocker):
    mock_client = mocker.Mock()
    mock_settings = mocker.Mock()
    mock_storage = mocker.Mock()

    plugin = ProjectPlugin(
        client=mock_client, settings=mock_settings, storage=mock_storage
    )

    mock_command = mocker.AsyncMock()
    mock_command.say = mocker.AsyncMock()

    for project in project_data.keys():
        mock_command.text = project
        await plugin.project(mock_command)

        if project in project_data:
            project_list = "\n".join(project_data[project])
            expected_message = (
                f"Hello , here the information about '{project}':\n{project_list}"
            )
        else:
            expected_message = f"Hello , the project '{project}' is not recognized. Please try different query."

        mock_command.say.assert_called_once_with(expected_message)
        mock_command.reset_mock()
