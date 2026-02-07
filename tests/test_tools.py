"""Tests for tool system."""

from agentkit.tools.base import ToolRegistry
from agentkit.tools.shell import ShellTool


def test_tool_registry():
    registry = ToolRegistry()
    shell = ShellTool()
    registry.register(shell)
    assert registry.get("shell") is shell
    assert "shell" in registry.list_tools()
    assert registry.get("nonexistent") is None


def test_tool_registry_describe():
    registry = ToolRegistry()
    registry.register(ShellTool())
    desc = registry.describe_all()
    assert "shell" in desc
    assert "Execute" in desc


def test_shell_tool_execute():
    shell = ShellTool()
    result = shell.execute(command="echo hello")
    assert result == "hello"


def test_shell_tool_metadata():
    shell = ShellTool()
    assert shell.name == "shell"
    assert "shell" in shell.description.lower() or "command" in shell.description.lower()
