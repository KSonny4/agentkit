# agentkit

Autonomous agent framework. Each agent = text files + Telegram bot. Runs forever.

## Setup (once)

**1. Install tools**

```bash
# Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Authenticate (opens browser)
claude

# uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. Create Telegram bot**

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`, follow prompts, copy the **bot token**
3. Message your new bot (say anything)
4. Get your chat ID:
   ```bash
   curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates" | python3 -m json.tool
   ```
   Find `"chat": {"id": 123456789}`

**3. Configure**

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=123456:ABC-xyz...
TELEGRAM_CHAT_ID=your-chat-id
```

**4. Install dependencies**

```bash
make install
```

## Run

```bash
make run                       # runs playground agent
make run PROFILE=nanoclaw      # runs nanoclaw agent
make run PROFILE=myagent       # runs any profile you created
```

That's it. The agent polls Telegram, processes messages through Claude, responds. Forever.

## Create an agent

```bash
mkdir profiles/myagent
```

Write three files:

**`profiles/myagent/identity.md`** — who the agent is, how it behaves

**`profiles/myagent/tools.md`** — what tools are available

**`profiles/myagent/evaluation.md`** — self-evaluation template

Then: `make run PROFILE=myagent`

## How it works

```
You message Telegram bot
  → agent receives message
  → processes through Claude Code CLI
  → sends response back to Telegram
  → MEMORY: lines saved to long-term memory
  → TELEGRAM: lines sent as notifications
  → waits for next message
  → forever
```
