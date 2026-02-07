"""Shell command execution tool."""

import subprocess

from agentkit.tools.base import Tool


class ShellTool(Tool):
    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return "Execute a shell command and return stdout."

    def execute(self, **kwargs) -> str:
        command = kwargs.get("command", "")
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 30s"
