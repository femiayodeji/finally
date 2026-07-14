"""Watchlist persistence: CRUD helpers over the `watchlist` table (PLAN.md §7).

Uses `get_connection()` from `app.db.database` (stdlib sqlite3, no new
dependency). All functions default to the single-user `user_id="default"`
scope, matching the rest of the DB layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.db.database import DEFAULT_USER_ID, get_connection


def list_tickers(user_id: str = DEFAULT_USER_ID) -> list[str]:
    """Return all watchlist tickers for the user, alphabetically sorted."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
    return [row["ticker"] for row in rows]


def add_ticker(ticker: str, user_id: str = DEFAULT_USER_ID) -> None:
    """Insert a ticker into the watchlist.

    Idempotent (WATCH-02) via `INSERT OR IGNORE`, honoring the
    UNIQUE(user_id, ticker) constraint in schema.sql — a duplicate add is a
    no-op, not an error.
    """
    now = datetime.now(UTC).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), user_id, ticker, now),
        )


def remove_ticker(ticker: str, user_id: str = DEFAULT_USER_ID) -> None:
    """Delete a ticker from the watchlist. No-op if not present."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )


def has_open_position(ticker: str, user_id: str = DEFAULT_USER_ID) -> bool:
    """True if the user holds a nonzero quantity of `ticker` (MKT-05).

    Consulted before untracking a removed watchlist ticker — a ticker with
    an open position must stay tracked even after leaving the watchlist
    (PLAN.md §6 Tracked Ticker Set). The `positions` table is empty this
    phase (portfolio APIs land in Plan 03), but the query must exist now so
    Plan 04's remove() rule is correct once positions exist.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM positions WHERE user_id = ? AND ticker = ? AND quantity > 0",
            (user_id, ticker),
        ).fetchone()
    return row is not None
