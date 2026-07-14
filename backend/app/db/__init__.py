"""SQLite persistence layer for FinAlly.

Public API:
    initialize          - Run schema creation then seeding (call once at app startup)
    init_db              - Create all tables if missing (idempotent)
    seed_default_data    - Insert default user + 10 default watchlist tickers (idempotent)
    get_connection        - Open a sqlite3 connection (row_factory=sqlite3.Row)
    get_db_path           - Resolve the SQLite file path (env-overridable)
    get_tracked_tickers   - Union of watchlist tickers and open-position tickers
"""

from .database import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    get_connection,
    get_db_path,
    get_tracked_tickers,
    init_db,
    initialize,
    seed_default_data,
)

__all__ = [
    "initialize",
    "init_db",
    "seed_default_data",
    "get_connection",
    "get_db_path",
    "get_tracked_tickers",
    "DEFAULT_USER_ID",
    "DEFAULT_CASH_BALANCE",
]
