"""Claude Code CLI wrapper — ALWAYS enforces Opus 4.6. READ-ONLY by default."""

import subprocess
from enum import Enum


class ClaudeError(Exception):
    """Raised when Claude CLI invocation fails."""


class ToolMode(Enum):
    READONLY = "readonly"
    READWRITE = "readwrite"


MODEL = "claude-opus-4-6"
DEFAULT_TIMEOUT = 600  # 10 minutes
READONLY_TOOLS = "Read,Glob,Grep,WebSearch,WebFetch"


def invoke_claude(
    prompt: str,
    *,
    context: str | None = None,
    system_prompt: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    output_format: str | None = None,
    tool_mode: ToolMode = ToolMode.READONLY,
) -> str:
    """Invoke Claude Code CLI and return the output.

    Model is ALWAYS claude-opus-4-6. No override possible.
    Default tool_mode is READONLY — write access requires explicit opt-in.
    """
    cmd = ["claude", "--print", "--model", MODEL]

    if tool_mode == ToolMode.READONLY:
        cmd.extend(["--allowedTools", READONLY_TOOLS])

    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    if output_format:
        cmd.extend(["--output-format", output_format])

    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            input=context,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=True,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise ClaudeError(f"Claude CLI timed out after {timeout}s")
    except subprocess.CalledProcessError as e:
        raise ClaudeError(f"Claude CLI failed: {e.stderr}")
