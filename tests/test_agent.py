"""Tests for core agent loop."""

from unittest.mock import patch

from agentkit.agent import Agent
from agentkit.claude import ToolMode
from agentkit.config import Config


def _make_agent(tmp_path):
    (tmp_path / "profiles" / "test").mkdir(parents=True)
    (tmp_path / "data").mkdir(exist_ok=True)
    config = Config(profile="test", project_root=tmp_path)
    return Agent(config)


@patch("agentkit.agent.invoke_claude")
def test_agent_process_task(mock_claude, tmp_path):
    mock_claude.return_value = "task completed successfully"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("do something", source="test")
    result = agent.process_next()
    assert result is True
    mock_claude.assert_called_once()


def test_agent_process_empty_queue(tmp_path):
    agent = _make_agent(tmp_path)
    result = agent.process_next()
    assert result is False


@patch("agentkit.agent.invoke_claude")
def test_agent_updates_memory_on_memory_prefix(mock_claude, tmp_path):
    mock_claude.return_value = "analysis done\nMEMORY: important finding"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("analyze data", source="test")
    agent.process_next()
    long_term = agent.memory.read_long_term()
    assert "important finding" in long_term


@patch("agentkit.agent.invoke_claude")
def test_agent_process_with_tool_mode(mock_claude, tmp_path):
    mock_claude.return_value = "done"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("write code", source="test")
    agent.process_next(tool_mode=ToolMode.READWRITE)
    _, kwargs = mock_claude.call_args
    assert kwargs["tool_mode"] == ToolMode.READWRITE
