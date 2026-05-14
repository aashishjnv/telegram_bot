"""
handlers/gmail.py
─────────────────
Full FSM flow for Gmail account creation requests.

Steps:
  1. Enter Full Name
  2. Enter Email Username
  3. Select Date of Birth (inline keyboard)
  4. Enter Password
  5. Confirm & submit (deducts 4 points, notifies admins)
"""

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database import db
from keyboards import (
    dob_keyboard,
    gmail_cancel_keyboard,
    gmail_confirm_keyboard,
    gmail_not_enough_points_keyboard,
    main_menu_keyboard,
)
from states import GmailStates

logger = logging.getLogger(__name__)
router = Router()

# Default DOB shown when user first opens the selector
_DEFAULT_YEAR, _DEFAULT_MONTH, _DEFAULT_DAY = 2000, 1, 15


# ── Entry: menu_gmail callback ────────────────────────────────────────────────

@router.callback_query(F.data == "menu_gmail")
async def gmail_start(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Error. Please /start again.", show_alert=True)
        return

    # Points gate
    if user.get("points", 0) < settings.GMAIL_POINTS_COST:
        await callback.message.edit_text(
            "╔══════════════════════════╗\n"
            "║     📧  CREATE GMAIL     ║\n"
            "╚══════════════════════════╝\n\n"
            f"⚠️ **Insufficient Points!**\n\n"
            f"You need minimum **{settings.GMAIL_POINTS_COST} points** to create a Gmail account.\n\n"
            f"⭐ Your current points: `{user.get('points', 0)}`\n"
            f"📉 Points needed: `{settings.GMAIL_POINTS_COST - user.get('points', 0)}`\n\n"
            "👥 Invite friends to earn more points!",
            reply_markup=gmail_not_enough_points_keyboard(),
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    await state.set_state(GmailStates.full_name)
    await callback.message.edit_text(
        "╔══════════════════════════╗\n"
        "║     📧  CREATE GMAIL     ║\n"
        "╚══════════════════════════╝\n\n"
        "**Step 1 of 4 — Full Name**\n\n"
        "✏️ Please enter the **full name** for the Gmail account:\n\n"
        "_Example: John Michael Smith_",
        reply_markup=gmail_cancel_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Step 1: Full Name ─────────────────────────────────────────────────────────

@router.message(GmailStates.full_name)
async def gmail_full_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3 or len(name) > 60:
        await message.answer(
            "⚠️ Name must be between 3 and 60 characters. Please try again.",
            reply_markup=gmail_cancel_keyboard(),
        )
        return

    await state.update_data(full_name=name)
    await state.set_state(GmailStates.email_username)
    await message.answer(
        "**Step 2 of 4 — Email Username**\n\n"
        f"✅ Name: **{name}**\n\n"
        "✏️ Enter the desired **email username** (part before @gmail.com):\n\n"
        "_Example: johnsmith2024_",
        reply_markup=gmail_cancel_keyboard(),
        parse_mode="Markdown",
    )


# ── Step 2: Email Username ────────────────────────────────────────────────────

@router.message(GmailStates.email_username)
async def gmail_email_username(message: Message, state: FSMContext):
    username = message.text.strip().lower()

    # Basic validation: only alphanumeric + dots
    import re
    if not re.match(r'^[a-z0-9][a-z0-9.]{4,28}[a-z0-9]$', username):
        await message.answer(
            "⚠️ Invalid username. Rules:\n"
            "• 6–30 characters\n"
            "• Lowercase letters, numbers, dots only\n"
            "• Cannot start/end with a dot\n\nPlease try again.",
            reply_markup=gmail_cancel_keyboard(),
        )
        return

    await state.update_data(email_username=username)
    await state.set_state(GmailStates.dob_select)

    data = await state.get_data()
    await message.answer(
        "**Step 3 of 4 — Date of Birth**\n\n"
        f"✅ Email: `{username}@gmail.com`\n\n"
        "📅 Select your **Date of Birth** using the buttons below:",
        reply_markup=dob_keyboard(_DEFAULT_YEAR, _DEFAULT_MONTH, _DEFAULT_DAY),
        parse_mode="Markdown",
    )


# ── Step 3: DOB navigation callbacks ─────────────────────────────────────────

@router.callback_query(GmailStates.dob_select, F.data.startswith("dob_"))
async def dob_navigate(callback: CallbackQuery, state: FSMContext):
    data_str = callback.data  # e.g. "dob_day_2000_1_16"

    if data_str == "dob_noop":
        await callback.answer()
        return

    parts = data_str.split("_")

    if parts[1] == "confirm":
        # dob_confirm_YEAR_MONTH_DAY
        year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
        dob_str = f"{day:02d}/{month:02d}/{year}"
        await state.update_data(dob=dob_str)
        await state.set_state(GmailStates.password)

        fsm_data = await state.get_data()
        await callback.message.edit_text(
            "**Step 4 of 4 — Password**\n\n"
            f"✅ Name: `{fsm_data.get('full_name')}`\n"
            f"✅ Email: `{fsm_data.get('email_username')}@gmail.com`\n"
            f"✅ DOB: `{dob_str}`\n\n"
            "🔐 Enter a **strong password** for the account:\n\n"
            "_Min 8 chars, mix letters, numbers & symbols_",
            reply_markup=gmail_cancel_keyboard(),
            parse_mode="Markdown",
        )
    else:
        # Navigation: parts = [dob, field, arg1, arg2, arg3]
        field = parts[1]  # day | month | year
        if field == "day":
            year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
        elif field == "month":
            year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
        elif field == "year":
            year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
        else:
            await callback.answer()
            return

        await callback.message.edit_reply_markup(
            reply_markup=dob_keyboard(year, month, day)
        )

    await callback.answer()


# ── Step 4: Password ──────────────────────────────────────────────────────────

@router.message(GmailStates.password)
async def gmail_password(message: Message, state: FSMContext):
    password = message.text.strip()

    if len(password) < 8:
        await message.answer(
            "⚠️ Password must be at least **8 characters**. Try again.",
            reply_markup=gmail_cancel_keyboard(),
            parse_mode="Markdown",
        )
        return

    await state.update_data(password=password)
    await state.set_state(GmailStates.confirm)
    data = await state.get_data()

    # Delete password message for security
    try:
        await message.delete()
    except Exception:
        pass

    await message.answer(
        "╔══════════════════════════╗\n"
        "║   📧  CONFIRM REQUEST    ║\n"
        "╚══════════════════════════╝\n\n"
        f"👤  **Name:** `{data['full_name']}`\n"
        f"📧  **Email:** `{data['email_username']}@gmail.com`\n"
        f"📅  **DOB:** `{data.get('dob', 'N/A')}`\n"
        f"🔐  **Password:** `{'*' * len(password)}`\n\n"
        f"💳  **Cost:** `{settings.GMAIL_POINTS_COST} points`\n\n"
        "✅ Confirm to submit your request?",
        reply_markup=gmail_confirm_keyboard(),
        parse_mode="Markdown",
    )


# ── Confirm: Submit ───────────────────────────────────────────────────────────

@router.callback_query(GmailStates.confirm, F.data == "gmail_submit")
async def gmail_submit(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    data = await state.get_data()

    # Re-check points atomically
    deducted = await db.remove_points(user_id, settings.GMAIL_POINTS_COST)
    if not deducted:
        await callback.message.edit_text(
            "⚠️ **Not enough points!**\nYour points may have changed. Please try again.",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        await state.clear()
        await callback.answer()
        return

    # Save request
    req = await db.create_gmail_request(
        user_id=user_id,
        full_name=data["full_name"],
        email_username=data["email_username"],
        dob=data.get("dob", "N/A"),
        password=data["password"],
    )

    await state.clear()

    db_user = await db.get_user(user_id)
    await callback.message.edit_text(
        "╔══════════════════════════╗\n"
        "║   ✅  REQUEST SUBMITTED  ║\n"
        "╚══════════════════════════╝\n\n"
        "🎉 Your Gmail account request has been submitted!\n\n"
        f"📧  **Email:** `{data['email_username']}@gmail.com`\n"
        f"⭐  **Remaining Points:** `{db_user.get('points', 0) if db_user else 0}`\n\n"
        "⏳ Admin will process your request shortly.\n"
        "You'll be notified once it's ready.",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )

    # ── Notify all admins ──────────────────────────────────────────────────
    tg_user = callback.from_user
    from keyboards import admin_requests_keyboard
    from bson import ObjectId

    req_id = str(req.get("_id", ""))
    admin_msg = (
        "📧 **NEW GMAIL REQUEST**\n\n"
        f"👤  User: @{tg_user.username or 'none'} (`{user_id}`)\n"
        f"📛  Name: {data['full_name']}\n"
        f"📧  Email: `{data['email_username']}@gmail.com`\n"
        f"📅  DOB: {data.get('dob', 'N/A')}\n"
        f"🔐  Password: `{data['password']}`\n"
    )

    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_msg,
                parse_mode="Markdown",
                reply_markup=admin_requests_keyboard(req_id, "pending") if req_id else None,
            )
        except Exception as e:
            logger.warning("Could not notify admin %s: %s", admin_id, e)

    await callback.answer("✅ Submitted!")
