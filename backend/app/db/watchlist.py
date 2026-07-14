"""Repository for `watchlist` — tickers the user is watching."""

from __future__ import annotations

from uuid import uuid4

from .connection import get_connection
from .util import now_iso


def list_watchlist(user_id: str = "default") -> list[str]:
    """Return watchlist tickers for the user, ordered by when they were added."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at",
            (user_id,),
        ).fetchall()
        return [row["ticker"] for row in rows]


def add_watchlist(ticker: str, user_id: str = "default") -> bool:
    """Add a ticker to the watchlist. Returns True if added, False if already present.

    Uses `INSERT OR IGNORE` against the `(user_id, ticker)` UNIQUE constraint so
    the add is idempotent and atomic (no separate existence check to race against).
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid4()), user_id, ticker, now_iso()),
        )
        return cursor.rowcount == 1


def remove_watchlist(ticker: str, user_id: str = "default") -> None:
    """Remove a ticker from the watchlist, if present."""
    with get_connection() as conn:
        conn.execute("DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker))


def is_watchlisted(ticker: str, user_id: str = "default") -> bool:
    """Return whether the ticker is currently on the user's watchlist."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
        ).fetchone()
        return row is not None
