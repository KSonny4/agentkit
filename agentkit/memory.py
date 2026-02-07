"""Memory management — daily observations + long-term knowledge."""

from datetime import date, timedelta
from pathlib import Path


class Memory:
    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir = memory_dir / "daily"
        self.daily_dir.mkdir(exist_ok=True)

    @property
    def _long_term_path(self) -> Path:
        return self.memory_dir / "MEMORY.md"

    def _daily_path(self, d: date | None = None) -> Path:
        d = d or date.today()
        return self.daily_dir / f"{d.isoformat()}.md"

    def read_long_term(self) -> str:
        path = self._long_term_path
        return path.read_text() if path.exists() else ""

    def write_long_term(self, content: str) -> None:
        self._long_term_path.write_text(content)

    def append_long_term(self, content: str) -> None:
        existing = self.read_long_term()
        separator = "\n\n" if existing else ""
        self._long_term_path.write_text(existing + separator + content)

    def read_today(self) -> str:
        path = self._daily_path()
        return path.read_text() if path.exists() else ""

    def append_today(self, content: str) -> None:
        path = self._daily_path()
        if not path.exists():
            header = f"# {date.today().isoformat()}\n\n"
            path.write_text(header + content + "\n")
        else:
            existing = path.read_text()
            path.write_text(existing + "\n" + content + "\n")

    def read_recent(self, days: int = 7) -> str:
        parts = []
        today = date.today()
        for i in range(days):
            d = today - timedelta(days=i)
            path = self._daily_path(d)
            if path.exists():
                parts.append(path.read_text())
        return "\n\n---\n\n".join(reversed(parts))
