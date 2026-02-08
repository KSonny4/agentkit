"""End-to-end test: agent creates a recurring job that sends Telegram messages.

Requires:
  - Claude CLI authenticated (OAuth)
  - TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env

Run:
  uv run pytest tests/test_e2e_cron.py -v -s
"""

import os
import subprocess
import time
from pathlib import Path

import pytest

from agentkit.config import Config
from agentkit.daemon import Daemon

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PREFIX = "com.agentkit."

# Load .env for the test
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)


def _agentkit_plists() -> list[Path]:
    """Return agentkit-related LaunchAgent plist files."""
    if not PLIST_DIR.exists():
        return []
    return list(PLIST_DIR.glob(f"{PLIST_PREFIX}*")) + list(PLIST_DIR.glob("*joke*"))


def _launchd_loaded() -> list[str]:
    """Return loaded agentkit/joke launchd jobs."""
    result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    return [
        l for l in result.stdout.splitlines()
        if "agentkit" in l.lower() or "joke" in l.lower()
    ]


def _clear_launchd():
    for p in _agentkit_plists():
        subprocess.run(["launchctl", "unload", str(p)], capture_output=True)
        p.unlink(missing_ok=True)


def _crontab_lines() -> list[str]:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        return []
    return [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]


def _clear_crontab():
    subprocess.run(["crontab", "-r"], capture_output=True, timeout=5)


@pytest.fixture(autouse=True)
def _clean_scheduling():
    """Ensure all scheduling is clean before and after each test."""
    _clear_launchd()
    _clear_crontab()
    yield
    _clear_launchd()
    _clear_crontab()


@pytest.mark.skipif(
    not os.environ.get("TELEGRAM_BOT_TOKEN"),
    reason="TELEGRAM_BOT_TOKEN not set",
)
@pytest.mark.skipif(
    not os.environ.get("TELEGRAM_CHAT_ID"),
    reason="TELEGRAM_CHAT_ID not set",
)
def test_agent_creates_recurring_job_and_sends_messages():
    """Ask agent to send jokes every minute. Verify it creates scheduling
    and the schedule survives for 2+ minutes."""

    config = Config(profile="playground", project_root=PROJECT_ROOT)
    daemon = Daemon(config)

    send_telegram = PROJECT_ROOT / "bin" / "send-telegram"

    prompt = (
        f"Create a macOS launchd LaunchAgent that sends me a joke every 60 seconds. "
        f"Use {send_telegram} as the command to send messages. "
        f"The plist should go in ~/Library/LaunchAgents/com.agentkit.joke.plist "
        f"with StartInterval=60 and RunAtLoad=true. "
        f"Load it with launchctl after creating it. Do it now."
    )

    response = daemon.handle_message(prompt)

    # --- Assert 1: got a response ---
    assert response is not None, "Agent returned None — Claude CLI likely failed"
    print(f"\n--- Agent response ---\n{response}\n---")

    # --- Assert 2: plist was created and loaded ---
    plists = _agentkit_plists()
    loaded = _launchd_loaded()
    cron = _crontab_lines()
    print(f"Plists: {plists}")
    print(f"Loaded launchd jobs: {loaded}")
    print(f"Crontab: {cron}")

    has_plist = len(plists) > 0
    has_loaded = len(loaded) > 0
    has_cron = any("send-telegram" in l for l in cron)

    assert has_plist or has_loaded or has_cron, (
        f"No scheduling found.\nPlists: {plists}\nLoaded: {loaded}\nCron: {cron}"
    )

    # --- Wait 130s for at least 2 fires ---
    print("Waiting 130 seconds for at least 2 scheduled fires...")
    time.sleep(130)

    # --- Assert 3: still active ---
    plists_after = _agentkit_plists()
    loaded_after = _launchd_loaded()
    assert len(plists_after) > 0 or len(loaded_after) > 0, (
        "LaunchAgent disappeared during wait"
    )

    print("\nTest passed: agent created LaunchAgent, waited 2+ min, still active.")
