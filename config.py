"""
config.py
─────────
Loads configuration from environment variables (or a .env file if present)
and exposes a single `settings` object used throughout the application.
"""

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class Settings:
    """Application settings read from environment variables."""

    def __init__(self):
        self.BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

        admin_ids_raw: str = os.environ.get("ADMIN_IDS", "")
        self.ADMIN_IDS: list[int] = [
            int(uid.strip())
            for uid in admin_ids_raw.split(",")
            if uid.strip().isdigit()
        ]

        self.MONGODB_URI: str = os.environ.get("MONGODB_URI", "")


settings = Settings()
