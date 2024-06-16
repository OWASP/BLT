# import pytest

# from lettuce.plugins.handle_messages import HandleMessagesPlugin


# @pytest.mark.asyncio
# async def test_handle_message(mocker):
#     mock_client = mocker.Mock()
#     mock_settings = mocker.Mock()
#     mock_storage = mocker.Mock()

#     plugin = HandleMessagesPlugin(
#              client=mock_client, settings=mock_settings, storage=mock_storage)

#     mock_command = mocker.AsyncMock()
#     mock_command.text = "@Lettuce contribute"
#     mock_command.reply = mocker.AsyncMock()

#     await plugin.handle_messages(mock_command)

#     mock_command.reply.assert_called_once_with(
#         "Please check the channel <#C077QBBLY1Z>" "for contributing guidelines today!"
#     )
