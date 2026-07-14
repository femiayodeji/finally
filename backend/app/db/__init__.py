"""SQLite persistence layer.

Public import surface — `from app.db import init_db, get_cash_balance, ...`
(see planning/BUILD_PLAN.md §4 for the contract this satisfies).
"""

from __future__ import annotations

from .chat import insert_message, recent_messages
from .connection import get_connection, get_db_path
from .init_db import init_db
from .positions import delete_position, get_position, list_positions, upsert_position
from .snapshots import insert_snapshot, list_snapshots
from .trades import insert_trade, list_trades
from .users import get_cash_balance, set_cash_balance
from .watchlist import add_watchlist, is_watchlisted, list_watchlist, remove_watchlist

__all__ = [
    "init_db",
    "get_db_path",
    "get_connection",
    "get_cash_balance",
    "set_cash_balance",
    "list_watchlist",
    "add_watchlist",
    "remove_watchlist",
    "is_watchlisted",
    "list_positions",
    "get_position",
    "upsert_position",
    "delete_position",
    "insert_trade",
    "list_trades",
    "insert_snapshot",
    "list_snapshots",
    "insert_message",
    "recent_messages",
]
