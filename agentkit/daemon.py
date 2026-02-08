"""Daemon mode — long-running Telegram-connected agent."""

import asyncio
import logging
import signal

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from agentkit.agent import Agent, TaskResult
from agentkit.claude import ToolMode
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

    def handle_message(self, text: str, source: str = "telegram") -> TaskResult | None:
        """Enqueue message, process, return TaskResult."""
        self.agent.mailbox.enqueue(text, source=source)
        return self.agent.process_next(tool_mode=ToolMode.READWRITE)

    def run(self) -> None:
        """Start Telegram polling. Blocks forever."""
        self.validate()
        log.info("Starting daemon with profile=%s", self.config.profile)
        asyncio.run(self._run_async())

    async def _run_async(self) -> None:
        app = ApplicationBuilder().token(self.config.telegram_bot_token).build()

        async def on_message(update: Update, context) -> None:
            if not update.message or not update.message.text:
                return

            user_text = update.message.text
            chat_id = str(update.message.chat_id)
            log.info("Received from chat %s: %s", chat_id, user_text[:80])

            result = await asyncio.to_thread(self.handle_message, user_text)

            if result:
                bot = TelegramBot(self.config.telegram_bot_token, chat_id)
                await bot.send(result.response)

                if result.pending_messages and self.config.telegram_chat_id:
                    notify_bot = TelegramBot(
                        self.config.telegram_bot_token, self.config.telegram_chat_id
                    )
                    for msg in result.pending_messages:
                        await notify_bot.send(msg)

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
        log.info("Telegram polling started — endless loop")

        async with app:
            await app.start()
            await app.updater.start_polling()

            stop_event = asyncio.Event()
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop_event.set)

            await stop_event.wait()
            await app.updater.stop()
            await app.stop()
