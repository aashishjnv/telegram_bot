"""
handlers/profile.py
───────────────────
Handles: Profile, Referral, Rewards, Help menu items.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from config import settings
from database import db
from keyboards import (
    back_to_main_keyboard,
    main_menu_keyboard,
    profile_keyboard,
    referral_keyboard,
)
from utils import format_help, format_profile, format_referral_info

logger = logging.getLogger(__name__)
router = Router()


# ── 👤 Profile ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return

    await callback.message.edit_text(
        format_profile(user),
        reply_markup=profile_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── 📊 Profile History ────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile_history")
async def show_history(callback: CallbackQuery):
    user_id = callback.from_user.id

    # Fetch last 5 Gmail requests
    gmail_list = await db.get_gmail_requests()
    user_gmail = [r for r in gmail_list if r["user_id"] == user_id][:5]

    # Fetch last 5 withdrawals
    withdrawals = await db.get_withdrawals(user_id=user_id)
    withdrawals = withdrawals[:5]

    lines = ["📋 **Your History**\n\n"]

    lines.append("📧 **Recent Gmail Requests:**")
    if user_gmail:
        for r in user_gmail:
            date = r["created_at"].strftime("%d %b") if r.get("created_at") else "N/A"
            lines.append(f"  • `{r['email_username']}@gmail.com` — {r['status'].upper()} ({date})")
    else:
        lines.append("  _No requests yet._")

    lines.append("\n💸 **Recent Withdrawals:**")
    if withdrawals:
        for w in withdrawals:
            date = w["created_at"].strftime("%d %b") if w.get("created_at") else "N/A"
            currency_sym = "₹" if w["currency"] == "inr" else "$"
            lines.append(
                f"  • {currency_sym}{w['amount']} via {w['method'].upper()} — {w['status'].upper()} ({date})"
            )
    else:
        lines.append("  _No withdrawals yet._")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_main_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── 👥 Referral ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_referral")
async def show_referral(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return

    await callback.message.edit_text(
        format_referral_info(user, settings.BOT_USERNAME),
        reply_markup=referral_keyboard(settings.BOT_USERNAME, callback.from_user.id),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── 🎁 Rewards ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_rewards")
async def show_rewards(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return

    text = (
        "╔══════════════════════════╗\n"
        "║       🎁  REWARDS        ║\n"
        "╚══════════════════════════╝\n\n"
        "🏆 **Current Balances:**\n\n"
        f"⭐  Points: `{user.get('points', 0)}`\n"
        f"🇮🇳  INR Balance: `₹{user.get('inr_balance', 0.0):.2f}`\n"
        f"💵  USD Balance: `${user.get('usd_balance', 0.0):.2f}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 **How to earn rewards:**\n"
        f"• Refer friends → earn **{settings.REFERRAL_POINTS} point(s)** each\n"
        "• Admin giveaways & bonuses\n"
        "• Complete tasks assigned by admin\n\n"
        "💸 Use **Withdraw** to cash out your balance!"
    )

    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── ℹ️ Help ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_help")
async def show_help(callback: CallbackQuery):
    await callback.message.edit_text(
        format_help(),
        reply_markup=back_to_main_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()
