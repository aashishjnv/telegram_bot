"""
handlers/admin.py
─────────────────
Complete admin panel.

Commands:   /admin  /adminhelp  /stats  /broadcast  /userinfo
            /addpoints  /removepoints  /addbalance  /removebalance
            /ban  /unban  /requests

All admin actions are gated by settings.is_admin(user_id).
Every action is logged to the admin_logs collection.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database import db
from keyboards import (
    admin_currency_keyboard,
    admin_panel_keyboard,
    admin_requests_keyboard,
    back_to_main_keyboard,
    main_menu_keyboard,
)
from states import AdminStates
from utils import format_admin_stats, format_user_info_admin

logger = logging.getLogger(__name__)
router = Router()


# ══════════════════════════════════════════════════════════════════════════════
# Guard helper
# ══════════════════════════════════════════════════════════════════════════════

async def _admin_gate(source: Message | CallbackQuery) -> bool:
    """Returns True if sender is an admin. Sends denial otherwise."""
    uid = source.from_user.id
    if settings.is_admin(uid):
        return True
    if isinstance(source, Message):
        await source.answer("🚫 Admin only command.")
    else:
        await source.answer("🚫 Admins only.", show_alert=True)
    return False


# ══════════════════════════════════════════════════════════════════════════════
# /admin  – Open panel
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not await _admin_gate(message):
        return
    await state.clear()
    await message.answer(
        "╔══════════════════════════╗\n"
        "║     🛠️  ADMIN PANEL      ║\n"
        "╚══════════════════════════╝\n\n"
        "Welcome, Admin! Choose an action below:",
        reply_markup=admin_panel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(Command("adminhelp"))
async def cmd_adminhelp(message: Message):
    if not await _admin_gate(message):
        return
    await message.answer(
        "**🛠 Admin Commands**\n\n"
        "/admin — Open admin panel\n"
        "/stats — Bot statistics\n"
        "/broadcast — Send message to all users\n"
        "/userinfo `<user_id>` — View user info\n"
        "/addpoints `<user_id> <points>` — Add points\n"
        "/removepoints `<user_id> <points>` — Remove points\n"
        "/addbalance `<user_id> <inr|usd> <amount>` — Add balance\n"
        "/removebalance `<user_id> <inr|usd> <amount>` — Remove balance\n"
        "/ban `<user_id> <reason>` — Ban user\n"
        "/unban `<user_id>` — Unban user\n"
        "/requests — View pending Gmail requests",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Stats
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("stats"))
@router.callback_query(F.data == "admin_stats")
async def admin_stats(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        if not await _admin_gate(event):
            return
        send = event.message.edit_text
        answer = event.answer
    else:
        if not await _admin_gate(event):
            return
        send = event.answer
        answer = None

    users = await db.get_user_count()
    referrals = await db.get_referral_count()
    gmail = await db.get_gmail_request_count()
    withdrawals = await db.get_withdrawal_count()
    active = await db.get_active_today()

    kwargs = dict(
        text=format_admin_stats(users, referrals, gmail, withdrawals, active),
        reply_markup=back_to_main_keyboard(),
        parse_mode="Markdown",
    )
    await send(**kwargs)
    if answer:
        await answer()


# ══════════════════════════════════════════════════════════════════════════════
# Broadcast
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("broadcast"))
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, CallbackQuery):
        if not await _admin_gate(event):
            return
        await event.message.edit_text(
            "📢 **Broadcast**\n\nSend the message you want to broadcast to all users.\n"
            "_(Supports text, photos, videos with captions)_",
            parse_mode="Markdown",
        )
        await event.answer()
    else:
        if not await _admin_gate(event):
            return
        await event.answer(
            "📢 **Broadcast**\n\nSend your broadcast message now:",
            parse_mode="Markdown",
        )
    await state.set_state(AdminStates.broadcast_message)


@router.message(AdminStates.broadcast_message)
async def admin_broadcast_send(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    users = await db.get_all_users()
    sent = 0
    failed = 0

    status_msg = await message.answer(f"📡 Broadcasting to {len(users)} users...")

    for user in users:
        if user.get("is_banned"):
            continue
        try:
            if message.photo:
                await bot.send_photo(
                    user["user_id"],
                    message.photo[-1].file_id,
                    caption=message.caption or "",
                    parse_mode="Markdown",
                )
            elif message.video:
                await bot.send_video(
                    user["user_id"],
                    message.video.file_id,
                    caption=message.caption or "",
                    parse_mode="Markdown",
                )
            else:
                await bot.send_message(
                    user["user_id"],
                    message.text or "",
                    parse_mode="Markdown",
                )
            sent += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ **Broadcast Complete**\n\n"
        f"📤 Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`"
    )
    await db.log_admin_action(message.from_user.id, "broadcast", details=f"sent={sent}, failed={failed}")


# ══════════════════════════════════════════════════════════════════════════════
# User Info
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("userinfo"))
async def cmd_userinfo(message: Message):
    if not await _admin_gate(message):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer("Usage: /userinfo `<user_id>`", parse_mode="Markdown")
        return
    await _send_userinfo(message, int(args[1].strip()))


@router.callback_query(F.data == "admin_userinfo")
async def admin_userinfo_prompt(callback: CallbackQuery, state: FSMContext):
    if not await _admin_gate(callback):
        return
    await state.set_state(AdminStates.waiting_user_id)
    await callback.message.edit_text("✏️ Enter the **User ID** to look up:", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.waiting_user_id)
async def admin_userinfo_input(message: Message, state: FSMContext):
    await state.clear()
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Invalid user ID.")
        return
    await _send_userinfo(message, int(message.text.strip()))


async def _send_userinfo(message: Message, user_id: int):
    user = await db.get_user(user_id)
    if not user:
        await message.answer(f"❌ User `{user_id}` not found.", parse_mode="Markdown")
        return
    await message.answer(format_user_info_admin(user), parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Add / Remove Points
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("addpoints"))
async def cmd_addpoints(message: Message, bot: Bot):
    if not await _admin_gate(message):
        return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("Usage: /addpoints `<user_id> <points>`", parse_mode="Markdown")
        return
    uid, pts = int(parts[1]), int(parts[2])
    user = await db.get_user(uid)
    if not user:
        await message.answer("❌ User not found.")
        return
    await db.add_points(uid, pts)
    await db.log_admin_action(message.from_user.id, "add_points", uid, f"+{pts}")
    await message.answer(f"✅ Added `{pts}` points to user `{uid}`.", parse_mode="Markdown")
    try:
        await bot.send_message(uid, f"🎉 Admin added **{pts} points** to your account!", parse_mode="Markdown")
    except Exception:
        pass


@router.callback_query(F.data == "admin_addpoints")
async def admin_addpoints_cb(callback: CallbackQuery, state: FSMContext):
    if not await _admin_gate(callback):
        return
    await state.set_state(AdminStates.add_points_user)
    await callback.message.edit_text("✏️ Enter **User ID** to add points:", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.add_points_user)
async def admin_addpoints_user(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Invalid ID.")
        return
    await state.update_data(target_user=int(message.text.strip()))
    await state.set_state(AdminStates.add_points_amount)
    await message.answer("✏️ Enter the number of **points** to add:")


@router.message(AdminStates.add_points_amount)
async def admin_addpoints_amount(message: Message, state: FSMContext, bot: Bot):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Invalid amount.")
        return
    data = await state.get_data()
    pts = int(message.text.strip())
    uid = data["target_user"]
    await state.clear()
    await db.add_points(uid, pts)
    await db.log_admin_action(message.from_user.id, "add_points", uid, f"+{pts}")
    await message.answer(f"✅ Added `{pts}` points to `{uid}`.", parse_mode="Markdown")
    try:
        await bot.send_message(uid, f"🎉 Admin added **{pts} points** to your account!", parse_mode="Markdown")
    except Exception:
        pass


@router.message(Command("removepoints"))
async def cmd_removepoints(message: Message, bot: Bot):
    if not await _admin_gate(message):
        return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("Usage: /removepoints `<user_id> <points>`", parse_mode="Markdown")
        return
    uid, pts = int(parts[1]), int(parts[2])
    success = await db.remove_points(uid, pts)
    if success:
        await db.log_admin_action(message.from_user.id, "remove_points", uid, f"-{pts}")
        await message.answer(f"✅ Removed `{pts}` points from `{uid}`.", parse_mode="Markdown")
    else:
        await message.answer("❌ Not enough points or user not found.")


@router.callback_query(F.data == "admin_removepoints")
async def admin_removepoints_cb(callback: CallbackQuery, state: FSMContext):
    if not await _admin_gate(callback):
        return
    await state.set_state(AdminStates.remove_points_user)
    await callback.message.edit_text("✏️ Enter **User ID** to remove points from:", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.remove_points_user)
async def admin_rmpoints_user(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Invalid ID.")
        return
    await state.update_data(target_user=int(message.text.strip()))
    await state.set_state(AdminStates.remove_points_amount)
    await message.answer("✏️ Enter the number of **points** to remove:")


@router.message(AdminStates.remove_points_amount)
async def admin_rmpoints_amount(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Invalid amount.")
        return
    data = await state.get_data()
    pts = int(message.text.strip())
    uid = data["target_user"]
    await state.clear()
    success = await db.remove_points(uid, pts)
    if success:
        await db.log_admin_action(message.from_user.id, "remove_points", uid, f"-{pts}")
        await message.answer(f"✅ Removed `{pts}` points from `{uid}`.", parse_mode="Markdown")
    else:
        await message.answer("❌ Insufficient points or user not found.")


# ══════════════════════════════════════════════════════════════════════════════
# Add / Remove Balance
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("addbalance"))
async def cmd_addbalance(message: Message, bot: Bot):
    if not await _admin_gate(message):
        return
    parts = message.text.split()
    if len(parts) != 4 or parts[2].lower() not in ("inr", "usd"):
        await message.answer("Usage: /addbalance `<user_id> <inr|usd> <amount>`", parse_mode="Markdown")
        return
    uid = int(parts[1])
    currency = parts[2].lower()
    try:
        amount = float(parts[3])
    except ValueError:
        await message.answer("❌ Invalid amount.")
        return
    await db.add_balance(uid, currency, amount)
    sym = "₹" if currency == "inr" else "$"
    await db.log_admin_action(message.from_user.id, "add_balance", uid, f"+{sym}{amount}")
    await message.answer(f"✅ Added `{sym}{amount}` to user `{uid}`.", parse_mode="Markdown")
    try:
        await bot.send_message(uid, f"💰 Admin added **{sym}{amount}** to your {currency.upper()} balance!", parse_mode="Markdown")
    except Exception:
        pass


@router.callback_query(F.data == "admin_addbalance")
async def admin_addbalance_cb(callback: CallbackQuery, state: FSMContext):
    if not await _admin_gate(callback):
        return
    await state.set_state(AdminStates.add_balance_user)
    await callback.message.edit_text("✏️ Enter **User ID** to add balance:", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.add_balance_user)
async def admin_addbal_user(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Invalid ID.")
        return
    await state.update_data(target_user=int(message.text.strip()))
    await state.set_state(AdminStates.add_balance_currency)
    await message.answer("Select currency:", reply_markup=admin_currency_keyboard("admbal"))


@router.callback_query(AdminStates.add_balance_currency, F.data.in_({"admbal_inr", "admbal_usd"}))
async def admin_addbal_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.replace("admbal_", "")
    await state.update_data(currency=currency)
    await state.set_state(AdminStates.add_balance_amount)
    await callback.message.edit_text(f"✏️ Enter **amount** to add ({currency.upper()}):", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.add_balance_amount)
async def admin_addbal_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Invalid amount.")
        return
    data = await state.get_data()
    uid, currency = data["target_user"], data["currency"]
    await state.clear()
    await db.add_balance(uid, currency, amount)
    sym = "₹" if currency == "inr" else "$"
    await db.log_admin_action(message.from_user.id, "add_balance", uid, f"+{sym}{amount}")
    await message.answer(f"✅ Added `{sym}{amount}` to `{uid}`.", parse_mode="Markdown")
    try:
        await bot.send_message(uid, f"💰 Admin added **{sym}{amount}** to your {currency.upper()} balance!", parse_mode="Markdown")
    except Exception:
        pass


@router.message(Command("removebalance"))
async def cmd_removebalance(message: Message):
    if not await _admin_gate(message):
        return
    parts = message.text.split()
    if len(parts) != 4 or parts[2].lower() not in ("inr", "usd"):
        await message.answer("Usage: /removebalance `<user_id> <inr|usd> <amount>`", parse_mode="Markdown")
        return
    uid = int(parts[1])
    currency = parts[2].lower()
    try:
        amount = float(parts[3])
    except ValueError:
        await message.answer("❌ Invalid amount.")
        return
    success = await db.remove_balance(uid, currency, amount)
    sym = "₹" if currency == "inr" else "$"
    if success:
        await db.log_admin_action(message.from_user.id, "remove_balance", uid, f"-{sym}{amount}")
        await message.answer(f"✅ Removed `{sym}{amount}` from `{uid}`.", parse_mode="Markdown")
    else:
        await message.answer("❌ Insufficient balance or user not found.")


@router.callback_query(F.data == "admin_removebalance")
async def admin_removebalance_cb(callback: CallbackQuery, state: FSMContext):
    if not await _admin_gate(callback):
        return
    await state.set_state(AdminStates.remove_balance_user)
    await callback.message.edit_text("✏️ Enter **User ID** to remove balance from:", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.remove_balance_user)
async def admin_rmbal_user(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Invalid ID.")
        return
    await state.update_data(target_user=int(message.text.strip()))
    await state.set_state(AdminStates.remove_balance_currency)
    await message.answer("Select currency:", reply_markup=admin_currency_keyboard("admrm"))


@router.callback_query(AdminStates.remove_balance_currency, F.data.in_({"admrm_inr", "admrm_usd"}))
async def admin_rmbal_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.replace("admrm_", "")
    await state.update_data(currency=currency)
    await state.set_state(AdminStates.remove_balance_amount)
    await callback.message.edit_text(f"✏️ Enter **amount** to remove ({currency.upper()}):", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.remove_balance_amount)
async def admin_rmbal_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Invalid amount.")
        return
    data = await state.get_data()
    uid, currency = data["target_user"], data["currency"]
    await state.clear()
    success = await db.remove_balance(uid, currency, amount)
    sym = "₹" if currency == "inr" else "$"
    if success:
        await db.log_admin_action(message.from_user.id, "remove_balance", uid, f"-{sym}{amount}")
        await message.answer(f"✅ Removed `{sym}{amount}` from `{uid}`.", parse_mode="Markdown")
    else:
        await message.answer("❌ Insufficient balance or user not found.")


# ══════════════════════════════════════════════════════════════════════════════
# Ban / Unban
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot):
    if not await _admin_gate(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer("Usage: /ban `<user_id> <reason>`", parse_mode="Markdown")
        return
    uid, reason = int(parts[1]), parts[2]
    await db.ban_user(uid, reason, message.from_user.id)
    await db.log_admin_action(message.from_user.id, "ban", uid, reason)
    await message.answer(f"🚫 User `{uid}` has been banned.\nReason: {reason}", parse_mode="Markdown")
    try:
        await bot.send_message(uid, f"🚫 You have been **banned** from this bot.\nReason: {reason}", parse_mode="Markdown")
    except Exception:
        pass


@router.callback_query(F.data == "admin_ban")
async def admin_ban_cb(callback: CallbackQuery, state: FSMContext):
    if not await _admin_gate(callback):
        return
    await state.set_state(AdminStates.ban_user_id)
    await callback.message.edit_text("✏️ Enter **User ID** to ban:", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.ban_user_id)
async def admin_ban_uid(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Invalid ID.")
        return
    await state.update_data(target_user=int(message.text.strip()))
    await state.set_state(AdminStates.ban_reason)
    await message.answer("✏️ Enter the **ban reason**:")


@router.message(AdminStates.ban_reason)
async def admin_ban_reason(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    uid = data["target_user"]
    reason = message.text.strip()
    await state.clear()
    await db.ban_user(uid, reason, message.from_user.id)
    await db.log_admin_action(message.from_user.id, "ban", uid, reason)
    await message.answer(f"🚫 User `{uid}` banned. Reason: {reason}", parse_mode="Markdown")
    try:
        await bot.send_message(uid, f"🚫 You have been **banned**.\nReason: {reason}", parse_mode="Markdown")
    except Exception:
        pass


@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot):
    if not await _admin_gate(message):
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Usage: /unban `<user_id>`", parse_mode="Markdown")
        return
    uid = int(parts[1])
    await db.unban_user(uid)
    await db.log_admin_action(message.from_user.id, "unban", uid)
    await message.answer(f"✅ User `{uid}` has been unbanned.", parse_mode="Markdown")
    try:
        await bot.send_message(uid, "✅ Your ban has been lifted. You can use the bot again.", parse_mode="Markdown")
    except Exception:
        pass


@router.callback_query(F.data == "admin_unban")
async def admin_unban_cb(callback: CallbackQuery, state: FSMContext):
    if not await _admin_gate(callback):
        return
    await state.set_state(AdminStates.unban_user_id)
    await callback.message.edit_text("✏️ Enter **User ID** to unban:", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.unban_user_id)
async def admin_unban_uid(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Invalid ID.")
        return
    uid = int(message.text.strip())
    await db.unban_user(uid)
    await db.log_admin_action(message.from_user.id, "unban", uid)
    await message.answer(f"✅ User `{uid}` unbanned.", parse_mode="Markdown")
    try:
        await bot.send_message(uid, "✅ Your ban has been lifted!", parse_mode="Markdown")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Requests
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("requests"))
@router.callback_query(F.data == "admin_requests")
async def admin_requests(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        if not await _admin_gate(event):
            return
        answer = event.answer
        send = event.message.answer
    else:
        if not await _admin_gate(event):
            return
        answer = None
        send = event.answer

    pending = await db.get_gmail_requests(status="pending", limit=10)

    if not pending:
        await send("📋 No pending Gmail requests at the moment. ✅")
        if answer:
            await answer()
        return

    for req in pending:
        req_id = str(req.get("_id", ""))
        text = (
            f"📧 **Gmail Request**\n\n"
            f"🆔 ID: `{req_id[:8]}...`\n"
            f"👤 User ID: `{req['user_id']}`\n"
            f"📛 Name: {req['full_name']}\n"
            f"📧 Email: `{req['email_username']}@gmail.com`\n"
            f"📅 DOB: {req.get('dob', 'N/A')}\n"
            f"🔐 Password: `{req.get('password', 'N/A')}`\n"
            f"📊 Status: **{req['status'].upper()}**"
        )
        await send(
            text,
            reply_markup=admin_requests_keyboard(req_id, req["status"]) if req_id else None,
            parse_mode="Markdown",
        )

    if answer:
        await answer()


# ── Request status update callbacks ──────────────────────────────────────────

@router.callback_query(F.data.startswith("req_"))
async def update_request_status(callback: CallbackQuery, bot: Bot):
    if not await _admin_gate(callback):
        return

    parts = callback.data.split("_", 2)
    # req_<status>_<id>
    status = parts[1]
    req_id = parts[2]

    await db.update_gmail_request(req_id, status)
    await db.log_admin_action(callback.from_user.id, f"req_{status}", details=req_id)

    await callback.message.edit_reply_markup(
        reply_markup=admin_requests_keyboard(req_id, status)
    )
    await callback.answer(f"✅ Marked as {status.upper()}")


# ── Admin cancel (FSM fallback) ───────────────────────────────────────────────

@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Action cancelled.",
        reply_markup=admin_panel_keyboard(),
    )
    await callback.answer()
