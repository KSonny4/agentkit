# agentkit

Minimal autonomous agent framework wrapping Claude Code CLI.
Each agent = text files. Telegram is primary I/O. Runs forever.

## Prerequisites

| What | How to get it |
|------|---------------|
| **Claude Code CLI** | `npm install -g @anthropic-ai/claude-code` |
| **Claude auth** | Run `claude` once, complete OAuth in browser |
| **uv** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Telegram bot** | Message [@BotFather](https://t.me/BotFather), `/newbot`, copy token |
| **Telegram chat ID** | Message your bot, then: `curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" \| python3 -m json.tool` — find `chat.id` |

## Quick start

```bash
# 1. Install
make install

# 2. Configure
cp .env.example .env
# Edit .env — fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 3. Run
make run                          # runs playground profile
make run PROFILE=nanoclaw          # runs nanoclaw profile
```

## One-off task (no Telegram needed)

```bash
make task PROMPT="What is 2+2?"
make task PROMPT="Analyze this repo" PROFILE=nanoclaw
make task PROMPT="Write tests" PROFILE=playground WRITE=1   # readwrite mode
```

## Create a new agent

```bash
mkdir profiles/myagent
```

Write three files:

- `profiles/myagent/identity.md` — who the agent is
- `profiles/myagent/tools.md` — what tools are available
- `profiles/myagent/evaluation.md` — self-evaluation template

Then run it:

```bash
make run PROFILE=myagent
```

## Docker

```bash
cp .env.example .env   # fill in all keys
docker compose up -d    # done
```

Override profile:

```bash
AGENT_PROFILE=nanoclaw docker compose up -d
```

## Commands

| Command | What it does |
|---------|-------------|
| `make install` | Install dependencies via uv |
| `make run` | Start Telegram daemon (default: playground) |
| `make run PROFILE=x` | Start daemon with profile x |
| `make task PROMPT="..."` | Run one-off task, print result |
| `make evaluate` | Run evaluation cycle |
| `make test` | Run test suite |
| `make lint` | Run ruff linter |
| `make check-auth` | Verify Claude CLI auth works |
| `make clean` | Remove caches |

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | For daemon | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | For notifications | Chat ID for TELEGRAM: directive messages |
| `AGENT_PROFILE` | No | Profile name (default: playground) |
| `ANTHROPIC_API_KEY` | No | Only if not using OAuth |

## How it works

```
Telegram message → Mailbox (SQLite) → Agent Loop → Claude Code CLI → Response
                                                                    ↓
                                                         MEMORY: → saved
                                                         TELEGRAM: → sent to chat
```

The daemon polls Telegram forever. Each message is queued, processed through Claude, and the response is sent back. `MEMORY:` lines get saved to long-term memory. `TELEGRAM:` lines get sent as notifications.
