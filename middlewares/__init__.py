"""
middlewares/__init__.py
───────────────────────
Two middleware classes:

  AntiSpamMiddleware  – Rate-limit users to SPAM_COOLDOWN_SECONDS per action.
  BanCheckMiddleware  – Block banned users from using the bot.
"""

import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery

from config import settings
from database import db

logger = logging.getLogger(__name__)

# Simple in-memory last-action timestamp per user_id
_last_action: Dict[int, float] = {}


class AntiSpamMiddleware(BaseMiddleware):
    """
    Rejects updates from users who are sending requests faster than
    SPAM_COOLDOWN_SECONDS.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        now = time.monotonic()
        last = _last_action.get(user.id, 0.0)

        if now - last < settings.SPAM_COOLDOWN_SECONDS:
            # Silently ignore the event (no error message to avoid spam)
            return None

        _last_action[user.id] = now
        return await handler(event, data)


class BanCheckMiddleware(BaseMiddleware):
    """
    Blocks every update from users who have been banned by an admin.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if await db.is_banned(user.id):
            # Inform user they're banned, then stop processing
            if isinstance(event, Message):
                await event.answer(
                    "🚫 You have been **banned** from using this bot.\n"
                    "Contact support if you believe this is a mistake.",
                    parse_mode="Markdown",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 You are banned.", show_alert=True)
            return None

        return await handler(event, data)
