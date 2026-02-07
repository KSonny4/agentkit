# /add-scheduler

Adds crontab-based scheduling support to your agentkit fork.

## What This Skill Does

- Creates `agentkit/scheduler.py` with Scheduler class (JSON schedule + crontab sync)
- Adds SCHEDULE: directive parsing to agent.py `_process_response()`
- Adds `schedule` subcommand to cli.py (list, add, remove, sync)
- Creates tests

## Steps

### 1. Create `agentkit/scheduler.py`

```python
"""Crontab-based self-scheduler — agent manages its own cron jobs."""

import json
import subprocess
from pathlib import Path


class Scheduler:
    CRON_TAG = "# agentkit-managed"

    def __init__(self, schedule_path: Path):
        self.schedule_path = schedule_path
        self.jobs = self._load()

    def _load(self) -> list[dict]:
        if self.schedule_path.exists():
            data = json.loads(self.schedule_path.read_text())
            return data.get("jobs", [])
        return []

    def _save(self) -> None:
        self.schedule_path.parent.mkdir(parents=True, exist_ok=True)
        self.schedule_path.write_text(json.dumps({"jobs": self.jobs}, indent=2))

    def add_job(self, name: str, command: str, profile: str, cron: str) -> None:
        if any(j["name"] == name for j in self.jobs):
            raise ValueError(f"Job '{name}' already exists")
        self.jobs.append({
            "name": name,
            "command": command,
            "profile": profile,
            "cron": cron,
            "enabled": True,
        })
        self._save()

    def remove_job(self, name: str) -> None:
        self.jobs = [j for j in self.jobs if j["name"] != name]
        self._save()

    def print_jobs(self) -> None:
        if not self.jobs:
            print("No scheduled jobs.")
            return
        for job in self.jobs:
            status = "enabled" if job.get("enabled", True) else "disabled"
            print(f"  {job['name']}: {job['command']} --profile {job['profile']} "
                  f"[{job['cron']}] ({status})")

    def sync_crontab(self, agentkit_bin: str = "agentkit") -> None:
        """Sync enabled jobs to crontab. Only touches agentkit-managed lines."""
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = result.stdout if result.returncode == 0 else ""

        # Strip old agentkit-managed lines
        lines = [line for line in existing.splitlines() if self.CRON_TAG not in line]

        # Add current enabled jobs
        for job in self.jobs:
            if job.get("enabled", True):
                entry = (f"{job['cron']} {agentkit_bin} {job['command']} "
                         f"--profile {job['profile']} {self.CRON_TAG}")
                lines.append(entry)

        new_crontab = "\n".join(lines) + "\n" if lines else ""
        subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
        enabled_count = len([j for j in self.jobs if j.get("enabled", True)])
        print(f"Synced {enabled_count} jobs to crontab.")
```

### 2. Add SCHEDULE: directive to agent.py

In `Agent.__init__()`, add `self.pending_schedules: list[str] = []`.

In `Agent._process_response()`, add:

```python
elif stripped.startswith("SCHEDULE:"):
    schedule = stripped[9:].strip()
    self.pending_schedules.append(schedule)
```

### 3. Add `schedule` subcommand to cli.py

Add to `create_parser()`:

```python
# agentkit schedule
sched_cmd = sub.add_parser("schedule", help="Manage scheduled jobs")
sched_sub = sched_cmd.add_subparsers(dest="schedule_action")
sched_sub.add_parser("list", help="List all scheduled jobs")
add_cmd = sched_sub.add_parser("add", help="Add a scheduled job")
add_cmd.add_argument("--name", required=True)
add_cmd.add_argument("--command", required=True)
add_cmd.add_argument("--profile", default="playground")
add_cmd.add_argument("--cron", required=True)
sched_sub.add_parser("remove", help="Remove a scheduled job").add_argument("--name", required=True)
sched_sub.add_parser("sync", help="Sync schedule to crontab")
```

Add to `main()`:

```python
elif args.command == "schedule":
    from agentkit.scheduler import Scheduler
    config = Config(profile="playground", project_root=Path.cwd())
    scheduler = Scheduler(config.schedule_path)

    if args.schedule_action == "list":
        scheduler.print_jobs()
    elif args.schedule_action == "add":
        scheduler.add_job(args.name, args.command, args.profile, args.cron)
    elif args.schedule_action == "remove":
        scheduler.remove_job(args.name)
    elif args.schedule_action == "sync":
        scheduler.sync_crontab()
```

### 4. Create `tests/test_scheduler.py`

```python
"""Tests for scheduler."""

import json

import pytest

from agentkit.scheduler import Scheduler


def test_load_empty_schedule(tmp_path):
    scheduler = Scheduler(tmp_path / "schedule.json")
    assert scheduler.jobs == []


def test_add_job(tmp_path):
    scheduler = Scheduler(tmp_path / "schedule.json")
    scheduler.add_job("evaluate", "evaluate", "trading", "0 */4 * * *")
    assert len(scheduler.jobs) == 1
    assert scheduler.jobs[0]["name"] == "evaluate"


def test_add_job_persists(tmp_path):
    path = tmp_path / "schedule.json"
    scheduler = Scheduler(path)
    scheduler.add_job("test", "task 'hello'", "playground", "* * * * *")
    data = json.loads(path.read_text())
    assert len(data["jobs"]) == 1


def test_remove_job(tmp_path):
    scheduler = Scheduler(tmp_path / "schedule.json")
    scheduler.add_job("test", "task 'hello'", "playground", "* * * * *")
    scheduler.remove_job("test")
    assert scheduler.jobs == []


def test_duplicate_job_name_rejected(tmp_path):
    scheduler = Scheduler(tmp_path / "schedule.json")
    scheduler.add_job("test", "task 'hello'", "playground", "* * * * *")
    with pytest.raises(ValueError, match="already exists"):
        scheduler.add_job("test", "task 'world'", "playground", "0 * * * *")


def test_sync_crontab_builds_correct_entries(tmp_path, monkeypatch):
    from unittest.mock import patch, MagicMock

    scheduler = Scheduler(tmp_path / "schedule.json")
    scheduler.add_job("eval", "evaluate", "trading", "0 */4 * * *")

    with patch("agentkit.scheduler.subprocess.run") as mock_run:
        # First call: crontab -l returns empty
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),  # no existing crontab
            MagicMock(returncode=0),  # crontab - succeeds
        ]
        scheduler.sync_crontab()
        # Check the input to crontab -
        second_call = mock_run.call_args_list[1]
        crontab_input = second_call[1]["input"]
        assert "0 */4 * * *" in crontab_input
        assert "agentkit-managed" in crontab_input
```

### 5. Verify

Run `pytest -v` to confirm all tests pass.
