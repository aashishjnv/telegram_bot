"""
states/__init__.py
──────────────────
All FSM state groups used across the bot.
"""

from aiogram.fsm.state import State, StatesGroup


class GmailStates(StatesGroup):
    """Multi-step Gmail account request flow."""
    full_name = State()
    email_username = State()
    dob_select = State()
    password = State()
    confirm = State()


class WithdrawStates(StatesGroup):
    """Multi-step withdrawal flow."""
    choose_method = State()
    enter_address = State()
    enter_amount = State()
    confirm = State()


class AdminStates(StatesGroup):
    """Admin panel conversation states."""
    broadcast_message = State()
    waiting_user_id = State()          # /userinfo
    add_points_user = State()
    add_points_amount = State()
    remove_points_user = State()
    remove_points_amount = State()
    add_balance_user = State()
    add_balance_currency = State()
    add_balance_amount = State()
    remove_balance_user = State()
    remove_balance_currency = State()
    remove_balance_amount = State()
    ban_user_id = State()
    ban_reason = State()
    unban_user_id = State()
