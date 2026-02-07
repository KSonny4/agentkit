# /add-self-evolution

Adds self-improvement capability to your agentkit fork.

## What This Skill Does

- Creates `agentkit/evolve.py` with self_improve(), _log_evolution(), _notify()
- Adds `self-improve` command to cli.py
- Creates tests

## Steps

### 1. Create `agentkit/evolve.py`

```python
"""Self-evolution — agent improves its own codebase."""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from agentkit.claude import ToolMode, invoke_claude
from agentkit.config import Config
from agentkit.context import ContextBuilder
from agentkit.memory import Memory

log = logging.getLogger(__name__)


def self_improve(config: Config) -> None:
    """Run self-improvement cycle.

    1. Create git branch
    2. Invoke Claude with READWRITE
    3. Run tests — if pass, commit; if fail, revert
    4. Log evolution attempt
    5. Notify via Telegram (if configured)
    """
    memory = Memory(config.memory_dir)
    context = ContextBuilder(config, memory)

    # Create evolution branch
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    branch = f"evolve/{timestamp}"
    subprocess.run(["git", "checkout", "-b", branch], check=True, capture_output=True)

    system_prompt = context.build_system_prompt()
    prompt = (
        "Review this codebase and make one focused improvement. "
        "Consider: code quality, test coverage, error handling, documentation. "
        "Make the change, then verify tests pass."
    )

    try:
        response = invoke_claude(
            prompt, system_prompt=system_prompt, tool_mode=ToolMode.READWRITE
        )

        # Run tests
        test_result = subprocess.run(
            ["python", "-m", "pytest", "-v"],
            capture_output=True, text=True, timeout=120
        )

        if test_result.returncode == 0:
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"evolve: self-improvement {timestamp}"],
                check=True, capture_output=True
            )
            _log_evolution(config.evolution_log_path, timestamp, "success", response[:200])
            log.info("Evolution succeeded: %s", branch)
        else:
            subprocess.run(["git", "checkout", "."], capture_output=True)
            subprocess.run(["git", "checkout", "-"], capture_output=True)
            _log_evolution(config.evolution_log_path, timestamp, "failed", test_result.stderr[:200])
            log.warning("Evolution failed tests, reverted: %s", branch)

    except Exception as e:
        subprocess.run(["git", "checkout", "."], capture_output=True)
        subprocess.run(["git", "checkout", "-"], capture_output=True)
        _log_evolution(config.evolution_log_path, timestamp, "error", str(e)[:200])
        log.error("Evolution error, reverted: %s", e)


def _log_evolution(log_path: Path, timestamp: str, status: str, details: str) -> None:
    """Append to evolution log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if log_path.exists():
        entries = json.loads(log_path.read_text())
    entries.append({
        "timestamp": timestamp,
        "status": status,
        "details": details,
    })
    log_path.write_text(json.dumps(entries, indent=2))


def _notify(config: Config, message: str) -> None:
    """Send evolution notification via Telegram if configured."""
    if config.telegram_bot_token:
        try:
            from agentkit.telegram_bot import TelegramBot
            bot = TelegramBot(config.telegram_bot_token, config.telegram_chat_id)
            bot.send_sync(message)
        except ImportError:
            log.debug("Telegram not available, skipping notification")
```

### 2. Add `self-improve` command to cli.py

Add to `create_parser()`:
```python
sub.add_parser("self-improve", help="Run self-improvement cycle (READWRITE)")
```

Add to `main()`:
```python
elif args.command == "self-improve":
    from agentkit.evolve import self_improve
    config = Config(profile="playground", project_root=Path.cwd())
    self_improve(config)
```

### 3. Create `tests/test_evolve.py`

```python
"""Tests for self-evolution."""

import json

from agentkit.evolve import _log_evolution


def test_log_evolution_creates_file(tmp_path):
    log_path = tmp_path / "evolution-log.json"
    _log_evolution(log_path, "2024-01-01-120000", "success", "improved tests")
    entries = json.loads(log_path.read_text())
    assert len(entries) == 1
    assert entries[0]["status"] == "success"


def test_log_evolution_appends(tmp_path):
    log_path = tmp_path / "evolution-log.json"
    _log_evolution(log_path, "2024-01-01-120000", "success", "first")
    _log_evolution(log_path, "2024-01-01-130000", "failed", "second")
    entries = json.loads(log_path.read_text())
    assert len(entries) == 2


def test_log_evolution_stores_details(tmp_path):
    log_path = tmp_path / "evolution-log.json"
    _log_evolution(log_path, "2024-01-01-120000", "error", "something broke")
    entries = json.loads(log_path.read_text())
    assert entries[0]["details"] == "something broke"


def test_log_evolution_stores_timestamp(tmp_path):
    log_path = tmp_path / "evolution-log.json"
    _log_evolution(log_path, "2024-01-01-120000", "success", "ok")
    entries = json.loads(log_path.read_text())
    assert entries[0]["timestamp"] == "2024-01-01-120000"
```

### 4. Verify

Run `pytest -v` to confirm all tests pass.
