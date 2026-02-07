"""Configuration — loads profile and environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    profile: str
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    model: str = field(default="claude-opus-4-6", init=False)

    @classmethod
    def from_env(cls) -> "Config":
        """Create Config from environment variables."""
        profile = os.environ.get("AGENT_PROFILE", "playground")
        return cls(profile=profile)

    @property
    def profile_dir(self) -> Path:
        return self.project_root / "profiles" / self.profile

    @property
    def memory_dir(self) -> Path:
        return self.project_root / "memory"

    @property
    def db_path(self) -> Path:
        return self.project_root / "data" / "agentkit.db"

    @property
    def schedule_path(self) -> Path:
        return self.project_root / "data" / "schedule.json"

    @property
    def evolution_log_path(self) -> Path:
        return self.project_root / "data" / "evolution-log.json"

    @property
    def telegram_bot_token(self) -> str:
        return os.environ.get("TELEGRAM_BOT_TOKEN", "")

    @property
    def telegram_chat_id(self) -> str:
        return os.environ.get("TELEGRAM_CHAT_ID", "")

