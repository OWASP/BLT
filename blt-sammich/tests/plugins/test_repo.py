import pytest

from sammich.plugins.repo import RepoPlugin


class TestRepoPlugin:
    """Repo plugin tests"""

    @pytest.fixture(autouse=True)
    def set_up(self, mocker):
        self.repo_plugin = RepoPlugin(
            client=mocker.Mock(), settings=mocker.Mock(), storage=mocker.Mock()
        )

        yield

    @pytest.mark.asyncio
    async def test_repo_command(self, mocker):
        mocker.patch.dict(
            self.repo_plugin.repo_data,
            {
                "test-1": [
                    "https://github.com/OWASP-BLT/test",
                    "https://github.com/OWASP-BLT/test1",
                ],
                "test-2": [
                    "https://github.com/OWASP-BLT/test",
                    "https://github.com/OWASP-BLT/test2",
                ],
            },
        )

        mock_command = mocker.AsyncMock()
        mock_command.say = mocker.AsyncMock()

        expected = {
            "test-1": (
                "Hello, you can implement your 'test-1' knowledge here:\n"
                "https://github.com/OWASP-BLT/test\nhttps://github.com/OWASP-BLT/test1"
            ),
            "test-2": (
                "Hello, you can implement your 'test-2' knowledge here:\n"
                "https://github.com/OWASP-BLT/test\nhttps://github.com/OWASP-BLT/test2"
            ),
        }

        for query, response in expected.items():
            mock_command.text = query
            await self.repo_plugin.repo(mock_command)
            mock_command.say.assert_called_once_with(response)
            mock_command.reset_mock()
