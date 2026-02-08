"""Tests for daemon mode."""

from unittest.mock import patch

import pytest

from agentkit.claude import ClaudeError
from agentkit.config import Config
from agentkit.daemon import Daemon


def _make_daemon(tmp_path):
    (tmp_path / "profiles" / "test").mkdir(parents=True)
    (tmp_path / "data").mkdir(exist_ok=True)
    config = Config(profile="test", project_root=tmp_path)
    return Daemon(config)


def test_daemon_init(tmp_path):
    daemon = _make_daemon(tmp_path)
    assert daemon.agent is not None
    assert daemon.config.profile == "test"


@patch("agentkit.agent.invoke_claude")
def test_handle_message_enqueues_and_processes(mock_claude, tmp_path):
    mock_claude.return_value = "I helped you\nMEMORY: user asked for help"
    daemon = _make_daemon(tmp_path)
    result = daemon.handle_message("help me")
    assert "I helped you" in result.response
    assert "MEMORY:" not in result.response


@patch("agentkit.agent.invoke_claude")
def test_handle_message_returns_none_on_error(mock_claude, tmp_path):
    mock_claude.side_effect = ClaudeError("fail")
    daemon = _make_daemon(tmp_path)
    assert daemon.handle_message("hello") is None


@patch("agentkit.agent.invoke_claude")
def test_handle_message_collects_pending(mock_claude, tmp_path):
    mock_claude.return_value = "ok\nTELEGRAM: notification"
    daemon = _make_daemon(tmp_path)
    result = daemon.handle_message("do thing")
    assert result.pending_messages == ["notification"]


def test_daemon_validate_requires_token(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    daemon = _make_daemon(tmp_path)
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        daemon.validate()


def test_daemon_validate_passes(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    daemon = _make_daemon(tmp_path)
    daemon.validate()  # should not raise
