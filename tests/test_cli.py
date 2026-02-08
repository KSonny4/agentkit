"""Tests for CLI."""

from unittest.mock import patch, MagicMock

from agentkit.agent import TaskResult
from agentkit.cli import create_parser, _send_pending


def test_parser_task_command():
    parser = create_parser()
    args = parser.parse_args(["task", "do something"])
    assert args.command == "task"
    assert args.prompt == "do something"


def test_parser_task_write_flag():
    parser = create_parser()
    args = parser.parse_args(["task", "--write", "do something"])
    assert args.write is True


def test_parser_task_readonly_default():
    parser = create_parser()
    args = parser.parse_args(["task", "do something"])
    assert args.write is False


def test_parser_evaluate_command():
    parser = create_parser()
    args = parser.parse_args(["evaluate", "--profile", "trading"])
    assert args.command == "evaluate"
    assert args.profile == "trading"


def test_parser_default_profile():
    parser = create_parser()
    args = parser.parse_args(["task", "test"])
    assert args.profile == "playground"


def test_parser_run_command():
    parser = create_parser()
    args = parser.parse_args(["run", "--profile", "nanoclaw"])
    assert args.command == "run"
    assert args.profile == "nanoclaw"


def test_parser_run_default_profile():
    parser = create_parser()
    args = parser.parse_args(["run"])
    assert args.profile == "playground"


def test_send_pending_with_messages():
    config = MagicMock()
    config.telegram_bot_token = "tok"
    config.telegram_chat_id = "123"
    result = TaskResult(response="ok", pending_messages=["hello", "world"])
    with patch("agentkit.cli.TelegramBot") as MockBot:
        _send_pending(config, result)
        assert MockBot.return_value.send_sync.call_count == 2


def test_send_pending_no_token():
    config = MagicMock()
    config.telegram_bot_token = ""
    result = TaskResult(response="ok", pending_messages=["hello"])
    with patch("agentkit.cli.TelegramBot") as MockBot:
        _send_pending(config, result)
        MockBot.assert_not_called()


def test_send_pending_none_result():
    config = MagicMock()
    config.telegram_bot_token = "tok"
    with patch("agentkit.cli.TelegramBot") as MockBot:
        _send_pending(config, None)
        MockBot.assert_not_called()
