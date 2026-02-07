# agentkit

## What Is This?

Minimal autonomous agent framework (~400 LOC core) wrapping Claude Code CLI.
Consumer agents import agentkit and bring their own profiles, tools, and domain knowledge.

## Philosophy: Skills over Features

Contributors don't add features to the core codebase. Instead, they contribute Claude Code
skills (e.g. `/add-telegram`) that transform your fork. You end up with clean code that does
exactly what you need. Core stays minimal, forks diverge intentionally.

## Non-Negotiable Rules

1. **Always Opus 4.6** — every Claude CLI call uses `--model claude-opus-4-6`. No exceptions.
2. **Small codebase** — target ~400 LOC core. If you can't understand it in 10 minutes, it's too complex.
3. **Domain agnostic** — no trading/game logic in core. Profiles add domain behavior.
4. **File-based memory** — human-readable Markdown, git-trackable.
5. **Single process** — no microservices, no message queues, no abstraction layers.
6. **READ-ONLY by default** — Claude CLI calls use ToolMode.READONLY unless explicitly opted in.

## Architecture

```
CLI / Cron → Mailbox (SQLite) → Agent Loop → Context Builder →
Claude CLI → Result Parser → Memory Update
```

### Core Modules (~400 LOC)
- `config.py` — Config dataclass, paths, env vars
- `claude.py` — Claude CLI wrapper, ToolMode enum (READONLY default)
- `memory.py` — Dual-layer: daily observations + long-term knowledge (Markdown files)
- `context.py` — Context builder with orientation ritual
- `mailbox.py` — SQLite FIFO task queue
- `agent.py` — Core loop: gather → act → verify → iterate
- `cli.py` — Minimal CLI: `task` and `evaluate` commands
- `tools/` — Tool ABC, registry, shell tool

### Skills (each transforms the fork)
- `/add-telegram` — Adds telegram_bot.py, TELEGRAM: directive, wires into CLI
- `/add-scheduler` — Adds scheduler.py, SCHEDULE: directive, schedule CLI commands
- `/add-self-evolution` — Adds evolve.py, self-improve CLI command
- `/add-playground` — Adds playground profile + smoke-test.sh
- `/add-profile` — Scaffolds a new custom profile

## Permissions: ToolMode

- `ToolMode.READONLY` (default): Read, Glob, Grep, WebSearch, WebFetch
- `ToolMode.READWRITE`: all tools (for self-improvement, --write flag)

## Response Directives (Core)

- `MEMORY:` — appended to long-term memory

Skills add more directives:
- `TELEGRAM:` — send message (added by /add-telegram)
- `SCHEDULE:` — proposed scheduled job (added by /add-scheduler)

## Profile Structure

```
profiles/<name>/
├── identity.md      # Who the agent is
├── tools.md         # What tools are available
└── evaluation.md    # Evaluation template
```

## How to Add a Feature

Don't add it to core. Write a skill instead:

1. Create `skills/<skill-name>/SKILL.md`
2. The SKILL.md contains step-by-step instructions for Claude Code
3. Users apply the skill to their fork: Claude reads SKILL.md and transforms the code
4. Result: clean code that does exactly what they need

## How to Create a Consumer Agent

1. Create a new repo
2. `pip install agentkit` (or add as dependency)
3. Create `profiles/<agent-name>/` with identity.md, tools.md, evaluation.md
4. Optionally add custom tools extending `agentkit.tools.base.Tool`
5. Run: `agentkit task --profile <agent-name> "your prompt"`

## Key Design Decisions

- **Why Claude Code CLI?** Full tool ecosystem (Bash, Read, Write, Edit, Grep, Glob) in one call.
- **Why mailbox pattern?** One queue, one processing loop. Simple.
- **Why profiles?** Same framework, different behaviors.
- **Why file-based memory?** Human-readable, git-trackable, editable.
- **Why skills over features?** Core stays small. Forks customize freely.
