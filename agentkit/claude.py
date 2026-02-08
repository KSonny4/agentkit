"""Claude Code CLI wrapper — ALWAYS enforces Opus 4.6. READ-ONLY by default."""

import json
import subprocess
from enum import Enum
from pathlib import Path


class ClaudeError(Exception):
    """Raised when Claude CLI invocation fails."""


class ToolMode(Enum):
    READONLY = "readonly"
    READWRITE = "readwrite"


MODEL = "claude-opus-4-6"
DEFAULT_TIMEOUT = 1800  # 30 minutes
READONLY_TOOLS = "Read,Glob,Grep,WebSearch,WebFetch"


def invoke_claude(
    prompt: str,
    *,
    context: str | None = None,
    system_prompt: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    output_format: str | None = None,
    tool_mode: ToolMode = ToolMode.READONLY,
    progress_path: Path | None = None,
) -> str:
    """Invoke Claude Code CLI and return the output.

    Model is ALWAYS claude-opus-4-6. No override possible.
    Default tool_mode is READONLY — write access requires explicit opt-in.
    When progress_path is set, streams output to that file for live monitoring.
    """
    cmd = ["claude", "-p", "--model", MODEL]

    if tool_mode == ToolMode.READONLY:
        cmd.extend(["--allowedTools", READONLY_TOOLS])
    elif tool_mode == ToolMode.READWRITE:
        cmd.append("--dangerously-skip-permissions")

    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    if progress_path:
        cmd.extend(["--verbose", "--output-format", "stream-json"])
        # With --verbose, prompt must go via stdin, not as argument
        stdin_text = prompt if not context else f"{prompt}\n\n{context}"
        return _invoke_with_progress(cmd, stdin_text=stdin_text, timeout=timeout,
                                     progress_path=progress_path)

    if output_format:
        cmd.extend(["--output-format", output_format])

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
        error = e.stderr or e.stdout or f"exit code {e.returncode}"
        raise ClaudeError(f"Claude CLI failed: {error}")


def _invoke_with_progress(cmd, *, stdin_text, timeout, progress_path):
    """Run Claude CLI streaming progress to a file for live monitoring."""
    progress_path = Path(progress_path)
    progress_path.parent.mkdir(parents=True, exist_ok=True)

    with open(progress_path, "w") as pf:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=pf,
            stderr=subprocess.PIPE,
            text=True,
        )
        process.stdin.write(stdin_text)
        process.stdin.close()

        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise ClaudeError(f"Claude CLI timed out after {timeout}s")

    if process.returncode != 0:
        stderr = process.stderr.read()
        raise ClaudeError(f"Claude CLI failed: {stderr or f'exit code {process.returncode}'}")

    # Parse final result from stream-json
    result_text = ""
    with open(progress_path) as pf:
        for line in pf:
            try:
                event = json.loads(line.strip())
                if event.get("type") == "result":
                    result_text = event.get("result", "")
            except (json.JSONDecodeError, KeyError):
                pass
    return result_text
