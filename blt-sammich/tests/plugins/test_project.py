import pytest

from sammich.plugins.project import ProjectPlugin


class TestProjectPlugin:
    """Project plugin tests."""

    @pytest.fixture(autouse=True)
    def set_up(self, mocker):
        self.project_plugin = ProjectPlugin(
            client=mocker.Mock(), settings=mocker.Mock(), storage=mocker.Mock()
        )
        yield

    @pytest.mark.asyncio
    async def test_no_project(self, mocker):
        mocker.patch.dict(self.project_plugin.project_data, {})

        mock_command = mocker.AsyncMock()
        mock_command.text = "xyx"
        mock_command.say = mocker.AsyncMock()

        await self.project_plugin.project(mock_command)

        mock_command.say.assert_called_once_with(
            "Hello, the project 'xyx' is not recognized. Please try different query."
        )
        mock_command.reset_mock()

    @pytest.mark.asyncio
    async def test_project(self, mocker):
        mocker.patch.dict(
            self.project_plugin.project_data,
            {
                "test-project-1": [
                    "OWASP Test Project 1",
                    "https://github.com/OWASP/test-project-1",
                ],
                "test-project-2": [
                    "OWASP Test Project 2",
                    "https://github.com/OWASP/test-project-2",
                ],
            },
        )

        mock_command = mocker.AsyncMock()
        mock_command.say = mocker.AsyncMock()

        expected = {
            "test-project-1": (
                "Hello, here the information about 'test-project-1':\n"
                "OWASP Test Project 1\nhttps://github.com/OWASP/test-project-1"
            ),
            "test-project-2": (
                "Hello, here the information about 'test-project-2':\n"
                "OWASP Test Project 2\nhttps://github.com/OWASP/test-project-2"
            ),
            "test-project-3": (
                "Hello, the project 'test-project-3' is not recognized. "
                "Please try different query."
            ),
        }
        for query, response in expected.items():
            mock_command.text = query
            await self.project_plugin.project(mock_command)
            mock_command.say.assert_called_once_with(response)
            mock_command.reset_mock()
