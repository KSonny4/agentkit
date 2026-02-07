"""Core agent loop — gather -> act -> verify -> iterate."""

import logging

from agentkit.claude import ClaudeError, ToolMode, invoke_claude
from agentkit.config import Config
from agentkit.context import ContextBuilder
from agentkit.mailbox import Mailbox
from agentkit.memory import Memory

log = logging.getLogger(__name__)


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.memory = Memory(config.memory_dir)
        self.mailbox = Mailbox(config.db_path)
        self.context = ContextBuilder(config, self.memory)

    def process_next(self, *, tool_mode: ToolMode = ToolMode.READONLY) -> bool:
        """Process the next task from the mailbox. Returns True if a task was processed."""
        task = self.mailbox.dequeue()
        if task is None:
            return False

        log.info("Processing task %d: %s", task["id"], task["content"][:80])

        try:
            system_prompt = self.context.build_system_prompt()
            task_prompt = self.context.build_task_prompt(task["content"])
            response = invoke_claude(
                task_prompt, system_prompt=system_prompt, tool_mode=tool_mode
            )
            self._process_response(response)
            self.mailbox.complete(task["id"], result=response[:500])
            self.memory.append_today(f"Task: {task['content'][:100]}\nResult: {response[:200]}")
            log.info("Task %d completed", task["id"])
        except ClaudeError as e:
            self.mailbox.fail(task["id"], error=str(e))
            log.error("Task %d failed: %s", task["id"], e)

        return True

    def _process_response(self, response: str) -> None:
        """Extract directives from Claude's response. Core only handles MEMORY:."""
        for line in response.split("\n"):
            stripped = line.strip()
            if stripped.startswith("MEMORY:"):
                fact = stripped[7:].strip()
                self.memory.append_long_term(fact)

    def run_all(self, *, tool_mode: ToolMode = ToolMode.READONLY) -> int:
        """Process all pending tasks. Returns count of tasks processed."""
        count = 0
        while self.process_next(tool_mode=tool_mode):
            count += 1
        return count
