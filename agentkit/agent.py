"""Core agent loop — gather -> act -> verify -> iterate."""

import logging
from dataclasses import dataclass, field

from agentkit.claude import ClaudeError, ToolMode, invoke_claude
from agentkit.config import Config
from agentkit.context import ContextBuilder
from agentkit.mailbox import Mailbox
from agentkit.memory import Memory

log = logging.getLogger(__name__)


@dataclass
class TaskResult:
    response: str
    pending_messages: list[str] = field(default_factory=list)


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.memory = Memory(config.memory_dir)
        self.mailbox = Mailbox(config.db_path)
        self.context = ContextBuilder(config, self.memory)

    def process_next(self, *, tool_mode: ToolMode = ToolMode.READONLY) -> TaskResult | None:
        """Process the next task. Returns TaskResult or None."""
        task = self.mailbox.dequeue()
        if task is None:
            return None

        log.info("Processing task %d: %s", task["id"], task["content"][:80])

        try:
            system_prompt = self.context.build_system_prompt()
            task_prompt = self.context.build_task_prompt(task["content"])
            response = invoke_claude(
                task_prompt, system_prompt=system_prompt, tool_mode=tool_mode,
                progress_path=self.config.progress_path,
            )
            pending_messages = self._extract_directives(response)
            clean = self._clean_response(response)
            self.mailbox.complete(task["id"], result=response[:500])
            self.memory.append_today(f"Task: {task['content'][:100]}\nResult: {response[:200]}")
            log.info("Task %d completed", task["id"])
            return TaskResult(response=clean, pending_messages=pending_messages)
        except ClaudeError as e:
            self.mailbox.fail(task["id"], error=str(e))
            log.error("Task %d failed: %s", task["id"], e)
            return None

    def _extract_directives(self, response: str) -> list[str]:
        """Extract directives from Claude's response. Returns pending messages."""
        pending_messages: list[str] = []
        for line in response.split("\n"):
            stripped = line.strip()
            if stripped.startswith("MEMORY:"):
                self.memory.append_long_term(stripped[7:].strip())
            elif stripped.startswith("TELEGRAM:"):
                pending_messages.append(stripped[9:].strip())
        return pending_messages

    @staticmethod
    def _clean_response(response: str) -> str:
        """Strip directive lines from response."""
        lines = []
        for line in response.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("MEMORY:") and not stripped.startswith("TELEGRAM:"):
                lines.append(line)
        return "\n".join(lines).strip()

    def run_all(self, *, tool_mode: ToolMode = ToolMode.READONLY) -> int:
        """Process all pending tasks. Returns count processed."""
        count = 0
        while self.process_next(tool_mode=tool_mode):
            count += 1
        return count
