"""Telegram integration — send and receive messages."""

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

    async def send(self, text: str, chat_id: str | None = None) -> None:
        """Send a message to the specified or default chat."""
        chat_id = chat_id or self.chat_id
        text = self._truncate(text)
        try:
            await self._bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            log.error("Failed to send Telegram message: %s", e)

    def send_sync(self, text: str, chat_id: str | None = None) -> None:
        """Synchronous wrapper for send."""
        asyncio.run(self.send(text, chat_id))

    @staticmethod
    def _truncate(text: str) -> str:
        if len(text) <= MAX_MESSAGE_LENGTH:
            return text
        return text[: MAX_MESSAGE_LENGTH - 20] + "\n\n... (truncated)"
