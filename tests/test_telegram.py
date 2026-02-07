"""Tests for Telegram integration."""

from unittest.mock import AsyncMock, patch

from agentkit.telegram_bot import TelegramBot, MAX_MESSAGE_LENGTH


def test_telegram_bot_init():
    bot = TelegramBot("fake-token", "fake-chat-id")
    assert bot.token == "fake-token"
    assert bot.chat_id == "fake-chat-id"


def test_truncate_short_message():
    assert TelegramBot._truncate("hello") == "hello"


def test_truncate_exact_limit():
    msg = "x" * MAX_MESSAGE_LENGTH
    assert TelegramBot._truncate(msg) == msg


def test_truncate_long_message():
    result = TelegramBot._truncate("x" * 5000)
    assert len(result) <= MAX_MESSAGE_LENGTH
    assert "truncated" in result


@patch("agentkit.telegram_bot.Bot")
def test_send_sync_calls_bot_api(MockBot):
    mock_instance = MockBot.return_value
    mock_instance.send_message = AsyncMock()
    bot = TelegramBot("fake-token", "123")
    bot.send_sync("hello sync")
    mock_instance.send_message.assert_called_once_with(chat_id="123", text="hello sync")


@patch("agentkit.telegram_bot.Bot")
def test_send_sync_swallows_errors(MockBot):
    mock_instance = MockBot.return_value
    mock_instance.send_message = AsyncMock(side_effect=Exception("net"))
    bot = TelegramBot("fake-token", "123")
    bot.send_sync("hello")  # must not raise
