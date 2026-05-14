"""
utils/__init__.py
─────────────────
Shared helper functions.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Channel membership check
# ══════════════════════════════════════════════════════════════════════════════

async def check_membership(bot: Bot, user_id: int) -> bool:
    """
    Returns True if *user_id* is a member/admin/owner of FORCE_CHANNEL.
    Returns False on any error (user not found, bot not admin, etc.).
    """
    channel = settings.FORCE_CHANNEL
    if not channel:
        return True  # No force-join configured – allow all

    # Normalise to "@handle" or numeric id
    if channel.lstrip("-").isdigit():
        chat_id: int | str = int(channel)
    else:
        chat_id = f"@{channel.lstrip('@')}"

    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ("member", "administrator", "creator", "restricted")
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning("Membership check failed for %s: %s", user_id, exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error in check_membership: %s", exc)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Message formatters
# ══════════════════════════════════════════════════════════════════════════════

def format_profile(user: dict) -> str:
    joined = user.get("joined_at")
    if isinstance(joined, datetime):
        joined_str = joined.strftime("%d %b %Y")
    else:
        joined_str = "N/A"

    return (
        "╔══════════════════════════╗\n"
        "║       👤  MY PROFILE      ║\n"
        "╚══════════════════════════╝\n\n"
        f"🆔  **User ID:** `{user['user_id']}`\n"
        f"👤  **Name:** {user.get('full_name', 'N/A')}\n"
        f"🔖  **Username:** @{user.get('username') or 'none'}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐  **Points:** `{user.get('points', 0)}`\n"
        f"🇮🇳  **INR Balance:** `₹{user.get('inr_balance', 0.0):.2f}`\n"
        f"💵  **USD Balance:** `${user.get('usd_balance', 0.0):.2f}`\n"
        f"👥  **Referrals:** `{user.get('referral_count', 0)}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅  **Joined:** {joined_str}"
    )


def format_welcome(user: dict) -> str:
    return (
        f"✨ **Welcome back, {user.get('full_name', 'Friend')}!**\n\n"
        "🚀 You're in the **Premium Earning Platform**.\n"
        "Refer friends, complete tasks, and withdraw your earnings!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ Points: `{user.get('points', 0)}`   "
        f"👥 Referrals: `{user.get('referral_count', 0)}`\n"
        f"🇮🇳 INR: `₹{user.get('inr_balance', 0.0):.2f}`   "
        f"💵 USD: `${user.get('usd_balance', 0.0):.2f}`\n\n"
        "📌 Use the menu below to get started:"
    )


def format_referral_info(user: dict, bot_username: str) -> str:
    ref_link = f"https://t.me/{bot_username}?start={user['user_id']}"
    return (
        "╔══════════════════════════╗\n"
        "║      👥  REFERRAL SYSTEM  ║\n"
        "╚══════════════════════════╝\n\n"
        "💡 **How it works:**\n"
        "• Share your unique link with friends\n"
        f"• Each friend who joins = **+{settings.REFERRAL_POINTS} point(s)**\n"
        f"• You need **{settings.GMAIL_POINTS_COST} points** to create a Gmail account\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Your Referrals:** `{user.get('referral_count', 0)}`\n"
        f"⭐ **Your Points:** `{user.get('points', 0)}`\n\n"
        "🔗 **Your Referral Link:**\n"
        f"`{ref_link}`"
    )


def format_help() -> str:
    return (
        "╔══════════════════════════╗\n"
        "║      ℹ️  HELP & GUIDE     ║\n"
        "╚══════════════════════════╝\n\n"
        "📌 **How to Earn:**\n"
        "• Refer friends using your referral link\n"
        f"• Each successful referral = {settings.REFERRAL_POINTS} point(s)\n\n"
        "📧 **Create Gmail Account:**\n"
        f"• Requires **{settings.GMAIL_POINTS_COST} points**\n"
        "• Follow the step-by-step wizard\n\n"
        "💰 **Withdraw:**\n"
        "• Supports: UPI • PayPal • Crypto\n"
        "• Admin reviews and approves withdrawals\n\n"
        "🎁 **Rewards:**\n"
        "• Admin distributes INR / USD / Points\n"
        "• Check your balance regularly\n\n"
        "💬 **Support:** Contact admin for help."
    )


def format_admin_stats(
    users: int,
    referrals: int,
    gmail: int,
    withdrawals: int,
    active_today: int,
) -> str:
    return (
        "╔══════════════════════════╗\n"
        "║    📊  BOT STATISTICS    ║\n"
        "╚══════════════════════════╝\n\n"
        f"👥  **Total Users:** `{users}`\n"
        f"🔗  **Total Referrals:** `{referrals}`\n"
        f"📧  **Gmail Requests:** `{gmail}`\n"
        f"💸  **Withdrawals:** `{withdrawals}`\n"
        f"🟢  **Active Today:** `{active_today}`"
    )


def format_user_info_admin(user: dict) -> str:
    joined = user.get("joined_at")
    joined_str = joined.strftime("%d %b %Y %H:%M") if isinstance(joined, datetime) else "N/A"
    banned = "🚫 YES" if user.get("is_banned") else "✅ NO"
    return (
        "╔══════════════════════════╗\n"
        "║      🔍  USER INFO        ║\n"
        "╚══════════════════════════╝\n\n"
        f"🆔  **ID:** `{user['user_id']}`\n"
        f"👤  **Name:** {user.get('full_name', 'N/A')}\n"
        f"🔖  **Username:** @{user.get('username') or 'none'}\n"
        f"🚫  **Banned:** {banned}\n\n"
        f"⭐  **Points:** `{user.get('points', 0)}`\n"
        f"🇮🇳  **INR:** `₹{user.get('inr_balance', 0.0):.2f}`\n"
        f"💵  **USD:** `${user.get('usd_balance', 0.0):.2f}`\n"
        f"👥  **Referrals:** `{user.get('referral_count', 0)}`\n\n"
        f"📅  **Joined:** {joined_str}"
    )
