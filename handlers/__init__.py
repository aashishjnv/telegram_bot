"""
handlers/__init__.py
────────────────────
Exports every router so main.py can include them with one import.
"""

from .admin import router as admin_router
from .gmail import router as gmail_router
from .profile import router as profile_router
from .start import router as start_router
from .withdraw import router as withdraw_router

__all__ = [
    "start_router",
    "profile_router",
    "gmail_router",
    "withdraw_router",
    "admin_router",
]
