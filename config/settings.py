"""
config/settings.py
──────────────────
Central configuration loader.
Reads every required value from environment variables (or .env file).
"""

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # ── Core bot ────────────────────────────────────────────────────────────
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    BOT_USERNAME: str = field(default_factory=lambda: os.getenv("BOT_USERNAME", ""))

    # ── Force-join channel ───────────────────────────────────────────────────
    # Can be "@channelname" or a numeric chat_id like "-1001234567890"
    FORCE_CHANNEL: str = field(default_factory=lambda: os.getenv("FORCE_CHANNEL", ""))

    # ── Admins ───────────────────────────────────────────────────────────────
    # Stored as a comma-separated string in ENV; parsed to a list of ints here
    ADMIN_IDS: List[int] = field(default_factory=list)

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "mongodb://localhost:27017/telegrambot"
        )
    )

    # ── Business rules ───────────────────────────────────────────────────────
    GMAIL_POINTS_COST: int = 4          # Points required to create a Gmail account
    REFERRAL_POINTS: int = 1            # Points awarded per successful referral
    SPAM_COOLDOWN_SECONDS: int = 2      # Minimum seconds between user actions

    def __post_init__(self):
        raw = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]

    def is_admin(self, user_id: int) -> bool:
        """Return True if *user_id* is in the admin list."""
        return user_id in self.ADMIN_IDS


# Single shared instance used throughout the project
settings = Settings()
