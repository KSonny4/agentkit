"""Tests for Claude CLI wrapper."""

from unittest.mock import patch, MagicMock
import subprocess

import pytest

from agentkit.claude import (
    ClaudeError,
    ToolMode,
    MODEL,
    READONLY_TOOLS,
    invoke_claude,
)


@patch("agentkit.claude.subprocess.run")
def test_invoke_claude_basic(mock_run):
    mock_run.return_value = MagicMock(stdout="response text")
    result = invoke_claude("hello")
    assert result == "response text"
    cmd = mock_run.call_args[0][0]
    assert "--model" in cmd
    assert MODEL in cmd


@patch("agentkit.claude.subprocess.run")
def test_invoke_claude_readonly_default(mock_run):
    mock_run.return_value = MagicMock(stdout="ok")
    invoke_claude("test")
    cmd = mock_run.call_args[0][0]
    assert "--allowedTools" in cmd
    assert READONLY_TOOLS in cmd


@patch("agentkit.claude.subprocess.run")
def test_invoke_claude_readwrite_no_restriction(mock_run):
    mock_run.return_value = MagicMock(stdout="ok")
    invoke_claude("test", tool_mode=ToolMode.READWRITE)
    cmd = mock_run.call_args[0][0]
    assert "--allowedTools" not in cmd


@patch("agentkit.claude.subprocess.run")
def test_invoke_claude_with_context(mock_run):
    mock_run.return_value = MagicMock(stdout="ok")
    invoke_claude("test", context="some context")
    kwargs = mock_run.call_args[1]
    assert kwargs["input"] == "some context"


@patch("agentkit.claude.subprocess.run")
def test_invoke_claude_with_system_prompt(mock_run):
    mock_run.return_value = MagicMock(stdout="ok")
    invoke_claude("test", system_prompt="be helpful")
    cmd = mock_run.call_args[0][0]
    assert "--system-prompt" in cmd
    assert "be helpful" in cmd


@patch("agentkit.claude.subprocess.run")
def test_invoke_claude_enforces_opus(mock_run):
    mock_run.return_value = MagicMock(stdout="ok")
    invoke_claude("test")
    cmd = mock_run.call_args[0][0]
    assert "claude-opus-4-6" in cmd


@patch("agentkit.claude.subprocess.run")
def test_invoke_claude_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=600)
    with pytest.raises(ClaudeError, match="timed out"):
        invoke_claude("test")


@patch("agentkit.claude.subprocess.run")
def test_invoke_claude_nonzero_exit(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd="claude", stderr="error msg"
    )
    with pytest.raises(ClaudeError, match="failed"):
        invoke_claude("test")
