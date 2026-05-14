"""
handlers/start.py
─────────────────
/start command handler.
• Registers new users (with optional referral).
• Enforces force-join check.
• Shows main menu.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database import db
from keyboards import force_join_keyboard, main_menu_keyboard
from utils import check_membership, format_welcome

logger = logging.getLogger(__name__)
router = Router()


# ── /start ────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    """Entry point for every user."""
    await state.clear()  # Reset any ongoing conversation

    user = message.from_user
    args = message.text.split(maxsplit=1)[1] if " " in message.text else None

    # ── Resolve referrer ──────────────────────────────────────────────────
    referred_by: int | None = None
    if args and args.isdigit():
        referrer_id = int(args)
        if referrer_id != user.id:
            referred_by = referrer_id

    # ── Ensure user exists in DB ──────────────────────────────────────────
    db_user = await db.get_user(user.id)
    is_new = db_user is None
    if is_new:
        db_user = await db.create_user(
            user_id=user.id,
            username=user.username or "",
            full_name=user.full_name or "",
            referred_by=referred_by,
        )
    else:
        # Keep name/username in sync
        await db.update_user(
            user.id,
            {"username": user.username or "", "full_name": user.full_name or ""},
        )
        db_user = await db.get_user(user.id)

    # ── Force-join check ──────────────────────────────────────────────────
    if settings.FORCE_CHANNEL and not await check_membership(bot, user.id):
        await message.answer(
            "🔒 **Access Restricted**\n\n"
            "You must join our official channel to use this bot.\n\n"
            "📢 Click the button below to join, then press **I've Joined**.",
            reply_markup=force_join_keyboard(),
            parse_mode="Markdown",
        )
        return

    # ── Process referral (only after membership confirmed) ────────────────
    if is_new and referred_by:
        success = await db.add_referral(referred_by, user.id)
        if success:
            try:
                await bot.send_message(
                    referred_by,
                    f"🎉 **New Referral!**\n\n"
                    f"👤 {user.full_name} just joined using your referral link!\n"
                    f"⭐ You earned **{settings.REFERRAL_POINTS} point(s)**.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass  # Referrer may have blocked the bot

    # ── Show welcome menu ─────────────────────────────────────────────────
    await message.answer(
        format_welcome(db_user),
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


# ── Force-join callback: "I've Joined" ────────────────────────────────────────

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: CallbackQuery, bot: Bot):
    user = callback.from_user

    if not await check_membership(bot, user.id):
        await callback.answer(
            "❌ You haven't joined yet! Please join the channel first.",
            show_alert=True,
        )
        return

    await callback.answer("✅ Verified!", show_alert=False)

    db_user = await db.get_user(user.id)
    if not db_user:
        db_user = await db.create_user(
            user_id=user.id,
            username=user.username or "",
            full_name=user.full_name or "",
        )

    await callback.message.edit_text(
        format_welcome(db_user),
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


# ── Back to main menu ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.clear()
    user = callback.from_user
    db_user = await db.get_user(user.id)

    if not db_user:
        await callback.answer()
        return

    await callback.message.edit_text(
        format_welcome(db_user),
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Cancel any active flow ────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel_flow")
async def cancel_flow(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    user = callback.from_user
    db_user = await db.get_user(user.id)

    await callback.message.edit_text(
        "❌ **Action cancelled.**\n\n" + (format_welcome(db_user) if db_user else ""),
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()
