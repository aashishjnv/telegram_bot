"""
handlers/start.py
─────────────────
/start command handler.
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
    await state.clear()

    user = message.from_user
    args = message.text.split(maxsplit=1)[1] if " " in message.text else None

    referred_by = None

    if args and args.isdigit():
        referrer_id = int(args)

        if referrer_id != user.id:
            referred_by = referrer_id

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
        await db.update_user(
            user.id,
            {
                "username": user.username or "",
                "full_name": user.full_name or "",
            },
        )

        db_user = await db.get_user(user.id)

    # ── Force Join ─────────────────────────────────────────

    if settings.FORCE_CHANNEL and not await check_membership(bot, user.id):

        await message.answer(
            "🔒 Access Restricted\n\n"
            "You must join our official channel to use this bot.\n\n"
            "📢 Join the channel then click 'I've Joined'.",
            reply_markup=force_join_keyboard(),
        )

        return

    # ── Referral System ───────────────────────────────────

    if is_new and referred_by:

        success = await db.add_referral(referred_by, user.id)

        if success:
            try:
                await bot.send_message(
                    referred_by,
                    f"🎉 New Referral!\n\n"
                    f"👤 {user.full_name} joined using your link.\n"
                    f"⭐ You earned {settings.REFERRAL_POINTS} point(s).",
                )

            except Exception:
                pass

    # ── Welcome Message ───────────────────────────────────

    await message.answer(
        format_welcome(db_user),
        reply_markup=main_menu_keyboard(),
    )


# ── Check Join Callback ──────────────────────────────────

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: CallbackQuery, bot: Bot):

    user = callback.from_user

    if not await check_membership(bot, user.id):

        await callback.answer(
            "❌ You haven't joined yet!",
            show_alert=True,
        )

        return

    await callback.answer("✅ Verified!")

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
    )


# ── Back Main ────────────────────────────────────────────

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
    )

    await callback.answer()


# ── Cancel Flow ──────────────────────────────────────────

@router.callback_query(F.data == "cancel_flow")
async def cancel_flow(callback: CallbackQuery, state: FSMContext, bot: Bot):

    await state.clear()

    user = callback.from_user

    db_user = await db.get_user(user.id)

    await callback.message.edit_text(
        "❌ Action cancelled.\n\n"
        + (format_welcome(db_user) if db_user else ""),
        reply_markup=main_menu_keyboard(),
    )

    await callback.answer()
