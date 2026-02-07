# /add-telegram

Adds Telegram messaging support to your agentkit fork.

## What This Skill Does

- Creates `agentkit/telegram_bot.py` with TelegramBot class
- Adds `python-telegram-bot>=21.0` dependency to pyproject.toml
- Adds TELEGRAM: directive parsing to agent.py `_process_response()`
- Adds `_send_pending()` helper to cli.py
- Wires pending messages into task + evaluate commands
- Creates tests

## Steps

### 1. Create `agentkit/telegram_bot.py`

```python
"""Telegram integration — send messages."""

import asyncio
import logging

from telegram import Bot

log = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096


class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self._bot = Bot(token=token)

    async def send(self, text: str) -> None:
        """Send a message to the configured chat."""
        text = self._truncate(text)
        try:
            await self._bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            log.error("Failed to send Telegram message: %s", e)

    def send_sync(self, text: str) -> None:
        """Synchronous wrapper for send."""
        asyncio.run(self.send(text))

    @staticmethod
    def _truncate(text: str) -> str:
        if len(text) <= MAX_MESSAGE_LENGTH:
            return text
        return text[: MAX_MESSAGE_LENGTH - 20] + "\n\n... (truncated)"
```

### 2. Add dependency to pyproject.toml

Add `"python-telegram-bot>=21.0"` to the `dependencies` list.

### 3. Add TELEGRAM: directive to agent.py

In `Agent._process_response()`, add a `self.pending_messages: list[str]` attribute to `__init__`,
and in the response parser add:

```python
elif stripped.startswith("TELEGRAM:"):
    message = stripped[9:].strip()
    self.pending_messages.append(message)
```

### 4. Add `_send_pending()` to cli.py

```python
def _send_pending(config: Config, agent: Agent) -> None:
    """Send pending Telegram messages if configured."""
    if agent.pending_messages and config.telegram_bot_token:
        from agentkit.telegram_bot import TelegramBot
        bot = TelegramBot(config.telegram_bot_token, config.telegram_chat_id)
        for msg in agent.pending_messages:
            bot.send_sync(msg)
```

### 5. Wire into task + evaluate commands

After `agent.process_next()` in both the `task` and `evaluate` handlers, add:
```python
_send_pending(config, agent)
```

### 6. Create `tests/test_telegram.py`

```python
"""Tests for Telegram integration."""

from agentkit.telegram_bot import TelegramBot


def test_telegram_bot_init():
    bot = TelegramBot("fake-token", "fake-chat-id")
    assert bot.token == "fake-token"
    assert bot.chat_id == "fake-chat-id"


def test_truncate_short_message():
    result = TelegramBot._truncate("hello")
    assert result == "hello"


def test_truncate_long_message():
    long_msg = "x" * 5000
    result = TelegramBot._truncate(long_msg)
    assert len(result) <= 4096
    assert "truncated" in result
```

### 7. Verify

Run `pytest -v` to confirm all tests pass.
