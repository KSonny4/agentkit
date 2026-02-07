"""CLI entry point — task, evaluate, run."""

import argparse
import logging
import os
from pathlib import Path

from agentkit.agent import Agent
from agentkit.claude import ToolMode
from agentkit.config import Config
from agentkit.telegram_bot import TelegramBot


def _send_pending(config: Config, agent: Agent) -> None:
    """Send pending TELEGRAM: messages if configured."""
    if agent.pending_messages and config.telegram_bot_token:
        bot = TelegramBot(config.telegram_bot_token, config.telegram_chat_id)
        for msg in agent.pending_messages:
            bot.send_sync(msg)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentkit", description="Autonomous agent framework")
    sub = parser.add_subparsers(dest="command")

    task_cmd = sub.add_parser("task", help="Process a single task")
    task_cmd.add_argument("prompt", help="Task to process")
    task_cmd.add_argument("--profile", default="playground")
    task_cmd.add_argument("--write", action="store_true", help="Enable READWRITE mode")

    eval_cmd = sub.add_parser("evaluate", help="Run evaluation cycle (always READONLY)")
    eval_cmd.add_argument("--profile", default="playground")

    run_cmd = sub.add_parser("run", help="Start daemon (Telegram polling)")
    run_cmd.add_argument(
        "--profile", default=os.environ.get("AGENT_PROFILE", "playground")
    )

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.command == "task":
        config = Config(profile=args.profile, project_root=Path.cwd())
        agent = Agent(config)
        tool_mode = ToolMode.READWRITE if args.write else ToolMode.READONLY
        agent.mailbox.enqueue(args.prompt, source="cli")
        result = agent.process_next(tool_mode=tool_mode)
        if result:
            print(result)
        _send_pending(config, agent)

    elif args.command == "evaluate":
        config = Config(profile=args.profile, project_root=Path.cwd())
        eval_path = config.profile_dir / "evaluation.md"
        if not eval_path.exists():
            print(f"No evaluation.md found at {eval_path}")
            return
        agent = Agent(config)
        eval_template = eval_path.read_text()
        agent.mailbox.enqueue(eval_template, source="cron-evaluate")
        agent.process_next(tool_mode=ToolMode.READONLY)
        _send_pending(config, agent)

    elif args.command == "run":
        from agentkit.daemon import Daemon

        config = Config(profile=args.profile, project_root=Path.cwd())
        daemon = Daemon(config)
        daemon.run()

    else:
        parser.print_help()
