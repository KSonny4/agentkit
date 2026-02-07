"""Daemon mode — long-running Telegram-connected agent."""

import asyncio
import logging
import signal

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
        self._running = True

    def validate(self) -> None:
        """Validate required config for daemon mode."""
        if not self.config.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required for daemon mode")

    def handle_message(self, text: str, source: str = "telegram") -> str | None:
        """Enqueue message, process, return clean response."""
        self.agent.mailbox.enqueue(text, source=source)
        return self.agent.process_next()

    async def _send_response(self, response: str, chat_id: str) -> None:
        """Send agent response + any pending TELEGRAM: messages."""
        bot = TelegramBot(self.config.telegram_bot_token, chat_id)
        await bot.send(response)

    async def _send_pending(self) -> None:
        """Send pending TELEGRAM: directive messages to notification channel."""
        if self.agent.pending_messages and self.config.telegram_chat_id:
            bot = TelegramBot(
                self.config.telegram_bot_token, self.config.telegram_chat_id
            )
            for msg in self.agent.pending_messages:
                await bot.send(msg)

    async def _heartbeat_loop(self) -> None:
        """Internal cron — runs heartbeat.md every HEARTBEAT_INTERVAL seconds."""
        interval = self.config.heartbeat_interval
        heartbeat_path = self.config.heartbeat_path

        if interval <= 0 or not heartbeat_path.exists():
            log.info("No heartbeat configured (interval=%d, exists=%s)", interval, heartbeat_path.exists())
            return

        log.info("Heartbeat every %ds from %s", interval, heartbeat_path.name)

        while self._running:
            await asyncio.sleep(interval)
            if not self._running:
                break

            try:
                prompt = heartbeat_path.read_text()
                log.info("Running heartbeat")
                response = await asyncio.to_thread(self.handle_message, prompt, "heartbeat")

                if response and self.config.telegram_chat_id:
                    await self._send_response(response, self.config.telegram_chat_id)
                await self._send_pending()
            except Exception as e:
                log.error("Heartbeat failed: %s", e)

    def run(self) -> None:
        """Start Telegram polling + heartbeat loop. Blocks forever."""
        self.validate()
        log.info("Starting daemon with profile=%s", self.config.profile)
        asyncio.run(self._run_async())

    async def _run_async(self) -> None:
        """Async entrypoint — runs Telegram polling and heartbeat concurrently."""
        app = ApplicationBuilder().token(self.config.telegram_bot_token).build()

        async def on_message(update: Update, context) -> None:
            if not update.message or not update.message.text:
                return

            user_text = update.message.text
            chat_id = str(update.message.chat_id)
            log.info("Received from chat %s: %s", chat_id, user_text[:80])

            response = await asyncio.to_thread(self.handle_message, user_text)

            if response:
                await self._send_response(response, chat_id)
            await self._send_pending()

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

        # Start heartbeat as background task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        log.info("Telegram polling started — endless loop")

        # python-telegram-bot's run_polling manages its own loop,
        # so we use the lower-level initialize/start/updater pattern
        async with app:
            await app.start()
            await app.updater.start_polling()

            # Wait until stopped
            stop_event = asyncio.Event()
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop_event.set)

            await stop_event.wait()

            self._running = False
            heartbeat_task.cancel()
            await app.updater.stop()
            await app.stop()
