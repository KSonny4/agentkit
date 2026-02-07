"""Context builder — assembles prompts from identity, memory, and tools.

Includes an orientation ritual: every invocation starts by reading recent
memory and progress, preventing the 'cold start' problem.
"""

from agentkit.config import Config
from agentkit.memory import Memory


class ContextBuilder:
    def __init__(self, config: Config, memory: Memory):
        self.config = config
        self.memory = memory

    def _read_profile_file(self, name: str) -> str:
        path = self.config.profile_dir / name
        return path.read_text() if path.exists() else ""

    def build_system_prompt(self) -> str:
        sections = []

        # Orientation ritual — what happened recently?
        recent = self.memory.read_recent(days=3)
        if recent:
            sections.append(f"## Recent Context (Orientation)\n\n{recent}")

        identity = self._read_profile_file("identity.md")
        if identity:
            sections.append(f"## Identity\n\n{identity}")

        tools = self._read_profile_file("tools.md")
        if tools:
            sections.append(f"## Available Tools\n\n{tools}")

        long_term = self.memory.read_long_term()
        if long_term:
            sections.append(f"## Long-Term Memory\n\n{long_term}")

        return "\n\n---\n\n".join(sections)

    def build_task_prompt(self, task: str) -> str:
        return (
            f"## Task\n\n{task}\n\n"
            "## Instructions\n\n"
            "1. Analyze the task using your identity, memory, and tools.\n"
            "2. Take action or provide analysis.\n"
            "3. Verify your output is correct before responding.\n"
            "4. State any observations worth remembering (prefix with MEMORY:).\n"
        )
