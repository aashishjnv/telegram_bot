"""
keyboards/__init__.py
─────────────────────
All InlineKeyboard and ReplyKeyboard builders used by the bot.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import settings


# ══════════════════════════════════════════════════════════════════════════════
# Force-Join
# ══════════════════════════════════════════════════════════════════════════════

def force_join_keyboard() -> InlineKeyboardMarkup:
    channel = settings.FORCE_CHANNEL
    if not channel.startswith("@") and not channel.startswith("http"):
        channel = f"@{channel}"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{settings.FORCE_CHANNEL.lstrip('@')}"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ I've Joined – Check Again", callback_data="check_join"),
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Main Menu
# ══════════════════════════════════════════════════════════════════════════════

def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👤 Profile", callback_data="menu_profile"),
        InlineKeyboardButton(text="📧 Create Gmail", callback_data="menu_gmail"),
    )
    builder.row(
        InlineKeyboardButton(text="💰 Withdraw", callback_data="menu_withdraw"),
        InlineKeyboardButton(text="🎁 Rewards", callback_data="menu_rewards"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Referral", callback_data="menu_referral"),
        InlineKeyboardButton(text="ℹ️ Help", callback_data="menu_help"),
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Profile
# ══════════════════════════════════════════════════════════════════════════════

def profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 My History", callback_data="profile_history"),
        InlineKeyboardButton(text="🔄 Refresh", callback_data="menu_profile"),
    )
    builder.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main"))
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Gmail Flow
# ══════════════════════════════════════════════════════════════════════════════

def gmail_not_enough_points_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👥 Invite Friends", callback_data="menu_referral"))
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="back_main"))
    return builder.as_markup()


def gmail_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_flow"))
    return builder.as_markup()


def dob_keyboard(year: int, month: int, day: int) -> InlineKeyboardMarkup:
    """Inline DOB selector. Shows current selection with +/- controls."""
    builder = InlineKeyboardBuilder()

    MONTHS = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    # Day row
    builder.row(
        InlineKeyboardButton(text="◀", callback_data=f"dob_day_{year}_{month}_{max(day-1,1)}"),
        InlineKeyboardButton(text=f"📅 {day:02d}", callback_data="dob_noop"),
        InlineKeyboardButton(text="▶", callback_data=f"dob_day_{year}_{month}_{min(day+1,31)}"),
    )
    # Month row
    builder.row(
        InlineKeyboardButton(text="◀", callback_data=f"dob_month_{year}_{max(month-1,1)}_{day}"),
        InlineKeyboardButton(text=f"🗓 {MONTHS[month-1]}", callback_data="dob_noop"),
        InlineKeyboardButton(text="▶", callback_data=f"dob_month_{year}_{min(month+1,12)}_{day}"),
    )
    # Year row
    builder.row(
        InlineKeyboardButton(text="◀", callback_data=f"dob_year_{max(year-1,1990)}_{month}_{day}"),
        InlineKeyboardButton(text=f"📆 {year}", callback_data="dob_noop"),
        InlineKeyboardButton(text="▶", callback_data=f"dob_year_{min(year+1,2005)}_{month}_{day}"),
    )
    # Confirm / Cancel
    builder.row(
        InlineKeyboardButton(text="✅ Confirm DOB", callback_data=f"dob_confirm_{year}_{month}_{day}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_flow"),
    )
    return builder.as_markup()


def gmail_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Submit Request", callback_data="gmail_submit"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_flow"),
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Withdraw Flow
# ══════════════════════════════════════════════════════════════════════════════

def withdraw_method_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇮🇳 UPI", callback_data="withdraw_upi"),
        InlineKeyboardButton(text="🌐 PayPal", callback_data="withdraw_paypal"),
    )
    builder.row(InlineKeyboardButton(text="₿ Crypto", callback_data="withdraw_crypto"))
    builder.row(InlineKeyboardButton(text="🏠 Back", callback_data="back_main"))
    return builder.as_markup()


def withdraw_currency_keyboard(method: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if method == "upi":
        builder.row(InlineKeyboardButton(text="🇮🇳 INR Balance", callback_data="wcurrency_inr"))
    elif method in ("paypal", "crypto"):
        builder.row(
            InlineKeyboardButton(text="💵 USD Balance", callback_data="wcurrency_usd"),
            InlineKeyboardButton(text="🇮🇳 INR Balance", callback_data="wcurrency_inr"),
        )
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_flow"))
    return builder.as_markup()


def withdraw_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Confirm Withdraw", callback_data="withdraw_confirm"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_flow"),
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Referral
# ══════════════════════════════════════════════════════════════════════════════

def referral_keyboard(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 Share Link", url=f"https://t.me/share/url?url={ref_link}&text=Join%20and%20earn%20rewards!"))
    builder.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main"))
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Help / Back
# ══════════════════════════════════════════════════════════════════════════════

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main"))
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Admin Panel
# ══════════════════════════════════════════════════════════════════════════════

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
        InlineKeyboardButton(text="📋 Requests", callback_data="admin_requests"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="👤 User Info", callback_data="admin_userinfo"),
    )
    builder.row(
        InlineKeyboardButton(text="➕ Add Points", callback_data="admin_addpoints"),
        InlineKeyboardButton(text="➖ Remove Points", callback_data="admin_removepoints"),
    )
    builder.row(
        InlineKeyboardButton(text="💰 Add Balance", callback_data="admin_addbalance"),
        InlineKeyboardButton(text="💸 Remove Balance", callback_data="admin_removebalance"),
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Ban User", callback_data="admin_ban"),
        InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban"),
    )
    return builder.as_markup()


def admin_currency_keyboard(prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇮🇳 INR", callback_data=f"{prefix}_inr"),
        InlineKeyboardButton(text="💵 USD", callback_data=f"{prefix}_usd"),
    )
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="admin_cancel"))
    return builder.as_markup()


def admin_requests_keyboard(req_id: str, current_status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if current_status != "processing":
        builder.row(InlineKeyboardButton(text="⚙️ Mark Processing", callback_data=f"req_processing_{req_id}"))
    if current_status != "completed":
        builder.row(InlineKeyboardButton(text="✅ Mark Completed", callback_data=f"req_completed_{req_id}"))
    if current_status != "rejected":
        builder.row(InlineKeyboardButton(text="❌ Reject", callback_data=f"req_rejected_{req_id}"))
    return builder.as_markup()
