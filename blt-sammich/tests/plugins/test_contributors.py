from unittest.mock import patch

import pytest

from sammich.plugins.contributors import ContributorPlugin, format_data


class TestContributorPlugin:
    @pytest.fixture
    def set_up(self, mocker):
        self.contributor_plugin = ContributorPlugin(
            client=mocker.Mock(), settings=mocker.Mock(), storage=mocker.Mock()
        )
        yield

    @pytest.mark.asyncio
    async def test_contributors(self, mocker, set_up):
        with patch.dict(
            self.contributor_plugin.__dict__,
            {"contributor_data": {"test1": {"prs": "1", "issues": "1", "comments": "0"}}},
        ):
            prs = [{"user": {"login": "user1"}}]
            issues = [{"user": {"login": "user1"}}]
            comments = []

            formatted = format_data(prs, issues, comments)

            expected_output_text = (
                "*Contributor Data*\n"
                "```\n"
                "User   PRs Merged  Issues Resolved  Comments \n"
                "-----  ----------  ---------------  ---------\n"
                "user1  1           1                0        \n"
                "\n```"
            )

            assert formatted[0]['text']['text'] == expected_output_text
