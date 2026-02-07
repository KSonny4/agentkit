"""Daemon mode — long-running Telegram-connected agent."""

import asyncio
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from agentkit.agent import Agent
from agentkit.config import Config
from agentkit.telegram_bot import TelegramBot

log = logging.getLogger(__name__)


class Daemon:
    def __init__(self, config: Config):
        self.config = config
        self.agent = Agent(config)

    def validate(self) -> None:
        """Validate required config for daemon mode."""
        if not self.config.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required for daemon mode")

    def handle_message(self, text: str, source: str = "telegram") -> str | None:
        """Enqueue message, process, return clean response."""
        self.agent.mailbox.enqueue(text, source=source)
        return self.agent.process_next()

    def run(self) -> None:
        """Start Telegram polling loop. Blocks forever."""
        self.validate()
        log.info("Starting daemon with profile=%s", self.config.profile)

        app = ApplicationBuilder().token(self.config.telegram_bot_token).build()

        async def on_message(update: Update, context) -> None:
            if not update.message or not update.message.text:
                return

            user_text = update.message.text
            chat_id = str(update.message.chat_id)
            log.info("Received from chat %s: %s", chat_id, user_text[:80])

            # Run blocking Claude CLI call in thread pool
            response = await asyncio.to_thread(self.handle_message, user_text)

            # Send main response back to user's chat
            if response:
                bot = TelegramBot(self.config.telegram_bot_token, chat_id)
                await bot.send(response)

            # Send TELEGRAM: directive messages to notification channel
            if self.agent.pending_messages and self.config.telegram_chat_id:
                notify_bot = TelegramBot(
                    self.config.telegram_bot_token, self.config.telegram_chat_id
                )
                for msg in self.agent.pending_messages:
                    await notify_bot.send(msg)

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
        log.info("Telegram polling started — endless loop")
        app.run_polling()
