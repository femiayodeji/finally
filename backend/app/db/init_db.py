"""Database lifecycle: idempotent schema creation and default-data seeding."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from .connection import get_connection
from .util import now_iso

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0
DEFAULT_WATCHLIST = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
]


def init_db() -> None:
    """Create tables if missing, then seed default data if the DB is empty.

    Safe to call on every startup: `CREATE TABLE IF NOT EXISTS` makes schema
    creation a no-op once applied, and seeding only runs when `users_profile`
    is empty (i.e. a fresh database).
    """
    schema_sql = _SCHEMA_PATH.read_text()
    with get_connection() as conn:
        conn.executescript(schema_sql)
        row = conn.execute("SELECT COUNT(*) AS n FROM users_profile").fetchone()
        if row["n"] == 0:
            _seed(conn)


def _seed(conn: sqlite3.Connection) -> None:
    """Insert the default user and default watchlist. Runs inside init_db's connection."""
    now = now_iso()
    conn.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )
    conn.executemany(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        [(str(uuid4()), DEFAULT_USER_ID, ticker, now) for ticker in DEFAULT_WATCHLIST],
    )
