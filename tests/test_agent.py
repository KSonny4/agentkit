"""Tests for core agent loop."""

from unittest.mock import patch

from agentkit.agent import Agent
from agentkit.claude import ToolMode, ClaudeError
from agentkit.config import Config


def _make_agent(tmp_path):
    (tmp_path / "profiles" / "test").mkdir(parents=True)
    (tmp_path / "data").mkdir(exist_ok=True)
    config = Config(profile="test", project_root=tmp_path)
    return Agent(config)


@patch("agentkit.agent.invoke_claude")
def test_agent_process_task_returns_response(mock_claude, tmp_path):
    mock_claude.return_value = "task completed successfully"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("do something", source="test")
    result = agent.process_next()
    assert result == "task completed successfully"
    mock_claude.assert_called_once()


def test_agent_process_empty_queue_returns_none(tmp_path):
    agent = _make_agent(tmp_path)
    assert agent.process_next() is None


@patch("agentkit.agent.invoke_claude")
def test_agent_updates_memory_on_memory_prefix(mock_claude, tmp_path):
    mock_claude.return_value = "analysis done\nMEMORY: important finding"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("analyze data", source="test")
    agent.process_next()
    assert "important finding" in agent.memory.read_long_term()


@patch("agentkit.agent.invoke_claude")
def test_agent_process_with_tool_mode(mock_claude, tmp_path):
    mock_claude.return_value = "done"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("write code", source="test")
    agent.process_next(tool_mode=ToolMode.READWRITE)
    _, kwargs = mock_claude.call_args
    assert kwargs["tool_mode"] == ToolMode.READWRITE


@patch("agentkit.agent.invoke_claude")
def test_agent_collects_telegram_directives(mock_claude, tmp_path):
    mock_claude.return_value = "result\nTELEGRAM: hello from agent\nMEMORY: a fact"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("do work", source="test")
    agent.process_next()
    assert agent.pending_messages == ["hello from agent"]


@patch("agentkit.agent.invoke_claude")
def test_agent_strips_directives_from_response(mock_claude, tmp_path):
    mock_claude.return_value = "useful answer\nMEMORY: fact\nTELEGRAM: notify\nmore text"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("task", source="test")
    result = agent.process_next()
    assert "MEMORY:" not in result
    assert "TELEGRAM:" not in result
    assert "useful answer" in result
    assert "more text" in result


@patch("agentkit.agent.invoke_claude")
def test_agent_pending_messages_reset_each_process(mock_claude, tmp_path):
    mock_claude.return_value = "TELEGRAM: first"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("task1", source="test")
    agent.mailbox.enqueue("task2", source="test")
    agent.process_next()
    assert agent.pending_messages == ["first"]
    mock_claude.return_value = "no directives"
    agent.process_next()
    assert agent.pending_messages == []


@patch("agentkit.agent.invoke_claude")
def test_agent_run_all(mock_claude, tmp_path):
    mock_claude.return_value = "done"
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("t1", source="test")
    agent.mailbox.enqueue("t2", source="test")
    assert agent.run_all() == 2


@patch("agentkit.agent.invoke_claude")
def test_agent_error_returns_none(mock_claude, tmp_path):
    mock_claude.side_effect = ClaudeError("boom")
    agent = _make_agent(tmp_path)
    agent.mailbox.enqueue("task", source="test")
    assert agent.process_next() is None
