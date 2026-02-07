# agentkit

## What Is This?

Minimal autonomous agent framework (~600 LOC core) wrapping Claude Code CLI.
Consumer agents import agentkit and bring their own profiles, tools, and domain knowledge.
Docker-deployable as a SaaS-like daemon with Telegram I/O.

## Philosophy: Skills over Features

Contributors don't add features to the core codebase. Instead, they contribute Claude Code
skills (e.g. `/add-telegram`) that transform your fork. You end up with clean code that does
exactly what you need. Core stays minimal, forks diverge intentionally.

## Non-Negotiable Rules

1. **Always Opus 4.6** — every Claude CLI call uses `--model claude-opus-4-6`. No exceptions.
2. **Small codebase** — target ~600 LOC core. If you can't understand it in 10 minutes, it's too complex.
3. **Domain agnostic** — no trading/game logic in core. Profiles add domain behavior.
4. **File-based memory** — human-readable Markdown, git-trackable.
5. **Single process** — no microservices, no message queues, no abstraction layers.
6. **READ-ONLY by default** — Claude CLI calls use ToolMode.READONLY unless explicitly opted in.

## Architecture

```
CLI / Cron / Telegram → Mailbox (SQLite) → Agent Loop → Context Builder →
Claude CLI → Result Parser → Memory Update + Telegram notifications
```

### Core Modules (~600 LOC)
- `config.py` — Config dataclass, paths, env vars, `Config.from_env()`
- `claude.py` — Claude CLI wrapper, ToolMode enum (READONLY default)
- `memory.py` — Dual-layer: daily observations + long-term knowledge (Markdown files)
- `context.py` — Context builder with orientation ritual
- `mailbox.py` — SQLite FIFO task queue
- `agent.py` — Core loop: gather → act → verify → iterate
- `cli.py` — CLI: `task`, `evaluate`, and `run` commands
- `telegram_bot.py` — Telegram Bot wrapper (send/receive messages)
- `daemon.py` — Long-running Telegram-connected agent daemon
- `tools/` — Tool ABC, registry, shell tool

### Docker Deployment
- `Dockerfile` — Node.js + Python + Claude CLI container
- `docker-compose.yml` — Single-command deploy
- `docker/entrypoint.sh` — Container entry point

### Skills (each transforms the fork)
- `/add-scheduler` — Adds scheduler.py, SCHEDULE: directive, schedule CLI commands
- `/add-self-evolution` — Adds evolve.py, self-improve CLI command
- `/add-profile` — Scaffolds a new custom profile

## Permissions: ToolMode

- `ToolMode.READONLY` (default): Read, Glob, Grep, WebSearch, WebFetch
- `ToolMode.READWRITE`: all tools (for self-improvement, --write flag)

## Response Directives (Core)

- `MEMORY:` — appended to long-term memory
- `TELEGRAM:` — send message via Telegram (pending_messages queue)

Skills add more directives:
- `SCHEDULE:` — proposed scheduled job (added by /add-scheduler)

## Profile Structure

```
profiles/<name>/
├── identity.md      # Who the agent is
├── tools.md         # What tools are available
└── evaluation.md    # Evaluation template
```

## Daemon Mode

Start with `agentkit run` or `docker-compose up`. The daemon:
1. Validates `TELEGRAM_BOT_TOKEN` is set
2. Starts Telegram polling loop
3. On each message: enqueue → process → respond
4. TELEGRAM: directives are sent to the notification channel (`TELEGRAM_CHAT_ID`)
5. Runs forever (restart: unless-stopped in Docker)

## Docker Deployment

```bash
# 1. Create profile
mkdir profiles/myagent/
# Write identity.md, tools.md, evaluation.md

# 2. Configure
cp .env.example .env  # fill in API keys

# 3. Deploy
docker-compose up -d
```

Environment variables:
- `ANTHROPIC_API_KEY` — required
- `TELEGRAM_BOT_TOKEN` — required for daemon mode
- `TELEGRAM_CHAT_ID` — notification channel
- `AGENT_PROFILE` — profile name (default: playground)

## How to Add a Feature

Don't add it to core. Write a skill instead:

1. Create `skills/<skill-name>/SKILL.md`
2. The SKILL.md contains step-by-step instructions for Claude Code
3. Users apply the skill to their fork: Claude reads SKILL.md and transforms the code
4. Result: clean code that does exactly what they need

## How to Create a Consumer Agent

1. Create a new repo
2. `uv add agentkit` (or add as dependency)
3. Create `profiles/<agent-name>/` with identity.md, tools.md, evaluation.md
4. Optionally add custom tools extending `agentkit.tools.base.Tool`
5. Run: `uv run agentkit task --profile <agent-name> "your prompt"`
6. Or deploy: `docker-compose up -d` with AGENT_PROFILE set

## Key Design Decisions

- **Why Claude Code CLI?** Full tool ecosystem (Bash, Read, Write, Edit, Grep, Glob) in one call.
- **Why mailbox pattern?** One queue, one processing loop. Simple.
- **Why profiles?** Same framework, different behaviors.
- **Why file-based memory?** Human-readable, git-trackable, editable.
- **Why skills over features?** Core stays small. Forks customize freely.
- **Why Telegram?** Primary I/O channel — humans interact via chat, agents respond.
- **Why Docker?** One command deploy. Each agent = one container.
