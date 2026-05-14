"""
database/mongo.py
─────────────────
Async MongoDB wrapper (Motor).

Collections
───────────
  users           – Every bot user, their balances, points, referral data
  referrals       – One document per successful referral
  gmail_requests  – Gmail account creation requests
  withdrawals     – Withdrawal requests (pending / approved / rejected)
  admin_logs      – Audit trail of admin actions
  bans            – Banned users
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING

from config import settings

logger = logging.getLogger(__name__)


class Database:
    """Single async database client shared across the bot."""

    def __init__(self):
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None

    # ──────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────

    async def connect(self):
        """Connect to MongoDB and ensure indexes exist."""
        self.client = motor.motor_asyncio.AsyncIOMotorClient(settings.DATABASE_URL)
        self.db = self.client.get_default_database()

        # Derive DB name from URL when no path is specified
        if self.db is None or self.db.name == "test":
            self.db = self.client["telegrambot"]

        await self._create_indexes()
        logger.info("✅ Connected to MongoDB: %s", self.db.name)

    async def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed.")

    async def _create_indexes(self):
        """Create sparse indexes for fast lookups."""
        await self.db.users.create_index([("user_id", ASCENDING)], unique=True)
        await self.db.referrals.create_index(
            [("referrer_id", ASCENDING), ("referred_id", ASCENDING)], unique=True
        )
        await self.db.gmail_requests.create_index([("user_id", ASCENDING)])
        await self.db.withdrawals.create_index([("user_id", ASCENDING)])
        await self.db.bans.create_index([("user_id", ASCENDING)], unique=True)

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    # ──────────────────────────────────────────────────────────────────────
    # Users
    # ──────────────────────────────────────────────────────────────────────

    async def get_user(self, user_id: int) -> Optional[Dict]:
        return await self.db.users.find_one({"user_id": user_id})

    async def create_user(
        self,
        user_id: int,
        username: str,
        full_name: str,
        referred_by: Optional[int] = None,
    ) -> Dict:
        """
        Insert a new user document.
        Returns the existing document unchanged if the user already exists.
        """
        existing = await self.get_user(user_id)
        if existing:
            return existing

        doc = {
            "user_id": user_id,
            "username": username or "",
            "full_name": full_name or "",
            "points": 0,
            "inr_balance": 0.0,
            "usd_balance": 0.0,
            "referral_count": 0,
            "referred_by": referred_by,
            "is_banned": False,
            "joined_at": self._now(),
            "last_active": self._now(),
        }
        await self.db.users.insert_one(doc)
        return doc

    async def update_user(self, user_id: int, update: Dict):
        """Generic field update with $set."""
        update["last_active"] = self._now()
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": update}, upsert=False
        )

    async def add_points(self, user_id: int, points: int):
        await self.db.users.update_one(
            {"user_id": user_id}, {"$inc": {"points": points}}
        )

    async def remove_points(self, user_id: int, points: int) -> bool:
        """Deduct points only if balance is sufficient. Returns True on success."""
        user = await self.get_user(user_id)
        if not user or user["points"] < points:
            return False
        await self.db.users.update_one(
            {"user_id": user_id}, {"$inc": {"points": -points}}
        )
        return True

    async def add_balance(self, user_id: int, currency: str, amount: float):
        """currency must be 'inr' or 'usd'."""
        field = f"{currency.lower()}_balance"
        await self.db.users.update_one(
            {"user_id": user_id}, {"$inc": {field: amount}}
        )

    async def remove_balance(self, user_id: int, currency: str, amount: float) -> bool:
        field = f"{currency.lower()}_balance"
        user = await self.get_user(user_id)
        if not user or user.get(field, 0) < amount:
            return False
        await self.db.users.update_one(
            {"user_id": user_id}, {"$inc": {field: -amount}}
        )
        return True

    async def get_all_users(self) -> List[Dict]:
        return await self.db.users.find({}).to_list(length=None)

    async def get_user_count(self) -> int:
        return await self.db.users.count_documents({})

    async def get_active_today(self) -> int:
        from datetime import timedelta
        cutoff = self._now().replace(hour=0, minute=0, second=0, microsecond=0)
        return await self.db.users.count_documents({"last_active": {"$gte": cutoff}})

    # ──────────────────────────────────────────────────────────────────────
    # Referrals
    # ──────────────────────────────────────────────────────────────────────

    async def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """
        Record a referral.  Returns True if this is a new, valid referral.
        Prevents duplicates and self-referrals at the DB level.
        """
        if referrer_id == referred_id:
            return False
        existing = await self.db.referrals.find_one(
            {"referred_id": referred_id}
        )
        if existing:
            return False  # Already referred by someone else
        try:
            await self.db.referrals.insert_one(
                {
                    "referrer_id": referrer_id,
                    "referred_id": referred_id,
                    "created_at": self._now(),
                }
            )
            # Increment referrer's count + award points
            await self.db.users.update_one(
                {"user_id": referrer_id},
                {"$inc": {"referral_count": 1, "points": settings.REFERRAL_POINTS}},
            )
            return True
        except Exception:
            return False  # Duplicate key – already inserted

    async def get_referral_count(self) -> int:
        return await self.db.referrals.count_documents({})

    # ──────────────────────────────────────────────────────────────────────
    # Gmail Requests
    # ──────────────────────────────────────────────────────────────────────

    async def create_gmail_request(
        self,
        user_id: int,
        full_name: str,
        email_username: str,
        dob: str,
        password: str,
    ) -> Dict:
        doc = {
            "user_id": user_id,
            "full_name": full_name,
            "email_username": email_username,
            "dob": dob,
            "password": password,
            "status": "pending",   # pending | processing | completed | rejected
            "created_at": self._now(),
        }
        await self.db.gmail_requests.insert_one(doc)
        return doc

    async def get_gmail_requests(
        self, status: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        query = {"status": status} if status else {}
        return (
            await self.db.gmail_requests.find(query)
            .sort("created_at", DESCENDING)
            .to_list(length=limit)
        )

    async def get_gmail_request_count(self) -> int:
        return await self.db.gmail_requests.count_documents({})

    async def update_gmail_request(self, request_id: Any, status: str):
        from bson import ObjectId
        await self.db.gmail_requests.update_one(
            {"_id": ObjectId(str(request_id))},
            {"$set": {"status": status, "updated_at": self._now()}},
        )

    # ──────────────────────────────────────────────────────────────────────
    # Withdrawals
    # ──────────────────────────────────────────────────────────────────────

    async def create_withdrawal(
        self,
        user_id: int,
        method: str,
        address: str,
        amount: float,
        currency: str,
    ) -> Dict:
        doc = {
            "user_id": user_id,
            "method": method,         # upi | paypal | crypto
            "address": address,
            "amount": amount,
            "currency": currency.lower(),  # inr | usd
            "status": "pending",      # pending | approved | rejected
            "created_at": self._now(),
        }
        await self.db.withdrawals.insert_one(doc)
        return doc

    async def get_withdrawals(
        self, user_id: Optional[int] = None, status: Optional[str] = None
    ) -> List[Dict]:
        query: Dict[str, Any] = {}
        if user_id:
            query["user_id"] = user_id
        if status:
            query["status"] = status
        return (
            await self.db.withdrawals.find(query)
            .sort("created_at", DESCENDING)
            .to_list(length=100)
        )

    async def get_withdrawal_count(self) -> int:
        return await self.db.withdrawals.count_documents({})

    # ──────────────────────────────────────────────────────────────────────
    # Bans
    # ──────────────────────────────────────────────────────────────────────

    async def ban_user(self, user_id: int, reason: str, admin_id: int):
        await self.db.bans.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "reason": reason,
                    "banned_by": admin_id,
                    "banned_at": self._now(),
                }
            },
            upsert=True,
        )
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": {"is_banned": True}}
        )

    async def unban_user(self, user_id: int):
        await self.db.bans.delete_one({"user_id": user_id})
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": {"is_banned": False}}
        )

    async def is_banned(self, user_id: int) -> bool:
        doc = await self.db.bans.find_one({"user_id": user_id})
        return doc is not None

    # ──────────────────────────────────────────────────────────────────────
    # Admin Logs
    # ──────────────────────────────────────────────────────────────────────

    async def log_admin_action(
        self, admin_id: int, action: str, target_id: Optional[int] = None, details: str = ""
    ):
        await self.db.admin_logs.insert_one(
            {
                "admin_id": admin_id,
                "action": action,
                "target_id": target_id,
                "details": details,
                "timestamp": self._now(),
            }
        )


# ── Shared singleton ──────────────────────────────────────────────────────────
db = Database()
