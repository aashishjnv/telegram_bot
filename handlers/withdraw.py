"""
handlers/withdraw.py
────────────────────
Multi-step withdrawal flow:
  1. Choose method (UPI / PayPal / Crypto)
  2. Choose currency (INR / USD depending on method)
  3. Enter withdrawal address
  4. Enter amount
  5. Confirm → deduct balance, save to DB, notify admins
"""

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database import db
from keyboards import (
    back_to_main_keyboard,
    main_menu_keyboard,
    withdraw_confirm_keyboard,
    withdraw_currency_keyboard,
    withdraw_method_keyboard,
)
from states import WithdrawStates

logger = logging.getLogger(__name__)
router = Router()

# Minimum withdrawal amounts (in respective currency)
MIN_WITHDRAWAL = {"inr": 50.0, "usd": 1.0}


# ── Entry ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_withdraw")
async def withdraw_start(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Error. Please /start again.", show_alert=True)
        return

    await state.set_state(WithdrawStates.choose_method)
    await callback.message.edit_text(
        "╔══════════════════════════╗\n"
        "║      💰  WITHDRAW        ║\n"
        "╚══════════════════════════╝\n\n"
        "**Select Withdrawal Method:**\n\n"
        f"🇮🇳  INR Balance: `₹{user.get('inr_balance', 0.0):.2f}`\n"
        f"💵  USD Balance: `${user.get('usd_balance', 0.0):.2f}`\n\n"
        "_Choose the method that suits you:_",
        reply_markup=withdraw_method_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Method selection ──────────────────────────────────────────────────────────

@router.callback_query(
    WithdrawStates.choose_method,
    F.data.in_({"withdraw_upi", "withdraw_paypal", "withdraw_crypto"}),
)
async def withdraw_method_selected(callback: CallbackQuery, state: FSMContext):
    method = callback.data.replace("withdraw_", "")
    await state.update_data(method=method)
    await state.set_state(WithdrawStates.enter_address)

    await callback.message.edit_text(
        f"**{method.upper()} Withdrawal**\n\n"
        "✏️ Enter your withdrawal address:\n\n"
        + {
            "upi": "_Example: yourname@upi or 9876543210@paytm_",
            "paypal": "_Example: youremail@paypal.com_",
            "crypto": "_Example: Your USDT TRC20 wallet address_",
        }.get(method, ""),
        reply_markup=back_to_main_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()

    # Store method, then ask for currency
    await callback.message.edit_text(
        f"**{method.upper()} Withdrawal — Choose Currency**\n\n"
        "Select which balance to withdraw from:",
        reply_markup=withdraw_currency_keyboard(method),
        parse_mode="Markdown",
    )


# ── Currency selection ────────────────────────────────────────────────────────

@router.callback_query(
    WithdrawStates.enter_address,
    F.data.in_({"wcurrency_inr", "wcurrency_usd"}),
)
async def withdraw_currency_selected(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.replace("wcurrency_", "")
    await state.update_data(currency=currency)

    fsm_data = await state.get_data()
    method = fsm_data.get("method", "")
    sym = "₹" if currency == "inr" else "$"
    min_amt = MIN_WITHDRAWAL[currency]

    await callback.message.edit_text(
        f"**{method.upper()} Withdrawal — Address**\n\n"
        "✏️ Enter your **withdrawal address/ID**:\n\n"
        + {
            "upi": "_Example: name@ybl or 9876543210@paytm_",
            "paypal": "_Example: yourname@gmail.com_",
            "crypto": "_Example: TRC20 wallet address_",
        }.get(method, ""),
        reply_markup=back_to_main_keyboard(),
        parse_mode="Markdown",
    )
    await state.set_state(WithdrawStates.enter_address)
    # Update state to signal address-input phase
    await state.update_data(currency=currency, waiting_for="address")
    await callback.answer()


# ── Address text input ────────────────────────────────────────────────────────

@router.message(WithdrawStates.enter_address)
async def withdraw_address_input(message: Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("⚠️ Invalid address. Please try again.")
        return

    await state.update_data(address=address)
    await state.set_state(WithdrawStates.enter_amount)

    fsm_data = await state.get_data()
    currency = fsm_data.get("currency", "inr")
    sym = "₹" if currency == "inr" else "$"
    min_amt = MIN_WITHDRAWAL[currency]

    user = await db.get_user(message.from_user.id)
    bal_field = f"{currency}_balance"
    current_bal = user.get(bal_field, 0.0) if user else 0.0

    await message.answer(
        f"**Enter Withdrawal Amount**\n\n"
        f"💳  Available: `{sym}{current_bal:.2f}`\n"
        f"📉  Minimum: `{sym}{min_amt}`\n\n"
        "✏️ Enter amount (numbers only):",
        parse_mode="Markdown",
        reply_markup=back_to_main_keyboard(),
    )


# ── Amount input ──────────────────────────────────────────────────────────────

@router.message(WithdrawStates.enter_amount)
async def withdraw_amount_input(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Please enter a valid number.")
        return

    fsm_data = await state.get_data()
    currency = fsm_data.get("currency", "inr")
    min_amt = MIN_WITHDRAWAL[currency]

    if amount < min_amt:
        sym = "₹" if currency == "inr" else "$"
        await message.answer(f"⚠️ Minimum withdrawal is `{sym}{min_amt}`. Please enter a larger amount.", parse_mode="Markdown")
        return

    # Check balance
    user = await db.get_user(message.from_user.id)
    bal_field = f"{currency}_balance"
    current_bal = user.get(bal_field, 0.0) if user else 0.0

    if amount > current_bal:
        sym = "₹" if currency == "inr" else "$"
        await message.answer(
            f"⚠️ **Insufficient balance!**\n"
            f"Available: `{sym}{current_bal:.2f}`\n"
            f"Requested: `{sym}{amount:.2f}`",
            parse_mode="Markdown",
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(WithdrawStates.confirm)

    sym = "₹" if currency == "inr" else "$"
    method = fsm_data.get("method", "N/A").upper()
    address = fsm_data.get("address", "N/A")

    await message.answer(
        "╔══════════════════════════╗\n"
        "║   💰  CONFIRM WITHDRAW   ║\n"
        "╚══════════════════════════╝\n\n"
        f"💳  **Method:** `{method}`\n"
        f"📍  **Address:** `{address}`\n"
        f"💵  **Amount:** `{sym}{amount:.2f}`\n"
        f"🏦  **Currency:** `{currency.upper()}`\n\n"
        "✅ Confirm this withdrawal?",
        reply_markup=withdraw_confirm_keyboard(),
        parse_mode="Markdown",
    )


# ── Confirm ───────────────────────────────────────────────────────────────────

@router.callback_query(WithdrawStates.confirm, F.data == "withdraw_confirm")
async def withdraw_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    data = await state.get_data()

    amount = data["amount"]
    currency = data["currency"]
    method = data["method"]
    address = data["address"]

    # Deduct balance
    success = await db.remove_balance(user_id, currency, amount)
    if not success:
        await callback.message.edit_text(
            "⚠️ **Insufficient balance.** Your balance may have changed.",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        await state.clear()
        await callback.answer()
        return

    # Save to DB
    await db.create_withdrawal(
        user_id=user_id,
        method=method,
        address=address,
        amount=amount,
        currency=currency,
    )
    await state.clear()

    sym = "₹" if currency == "inr" else "$"
    await callback.message.edit_text(
        "╔══════════════════════════╗\n"
        "║  ✅  WITHDRAWAL PLACED   ║\n"
        "╚══════════════════════════╝\n\n"
        f"💳  Method: **{method.upper()}**\n"
        f"📍  Address: `{address}`\n"
        f"💵  Amount: **{sym}{amount:.2f}**\n\n"
        "⏳ Your withdrawal is under review.\n"
        "Admin will process it within 24 hours.",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )

    # Notify admins
    tg_user = callback.from_user
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💸 **WITHDRAWAL REQUEST**\n\n"
                f"👤 User: @{tg_user.username or 'none'} (`{user_id}`)\n"
                f"💳 Method: `{method.upper()}`\n"
                f"📍 Address: `{address}`\n"
                f"💵 Amount: `{sym}{amount:.2f}`\n"
                f"🏦 Currency: `{currency.upper()}`",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning("Could not notify admin %s: %s", admin_id, e)

    await callback.answer("✅ Withdrawal placed!")
