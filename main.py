"""
main.py
───────
Bot entry point.

• Connects to MongoDB.
• Registers middlewares and routers.
• Starts polling.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database import db
from handlers import (
    admin_router,
    gmail_router,
    profile_router,
    start_router,
    withdraw_router,
)
from middlewares import AntiSpamMiddleware, BanCheckMiddleware

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── Startup / Shutdown ────────────────────────────────────────────────────────

async def on_startup(bot: Bot):
    """Called once before the bot starts polling."""
    await db.connect()

    me = await bot.get_me()
    logger.info("🤖 Bot started: @%s (ID: %s)", me.username, me.id)

    # Notify admins
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"✅ <b>Bot Online</b>\n\n"
                f"@{me.username} is now running!\n"
                f"Database connected ✅",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")


async def on_shutdown(bot: Bot):
    """Called once when the bot is stopping."""
    await db.disconnect()
    logger.info("👋 Bot stopped.")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Check your .env file.")
        sys.exit(1)

    # Initialise bot + dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # ── Register middlewares ──────────────────────────────
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())
    dp.message.middleware(AntiSpamMiddleware())
    dp.callback_query.middleware(AntiSpamMiddleware())

    # ── Register routers ──────────────────────────────────
    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(gmail_router)
    dp.include_router(withdraw_router)

    # ── Lifecycle hooks ───────────────────────────────────
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ── Start polling ─────────────────────────────────────
    logger.info("🚀 Starting bot polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
