"""Repository for `positions` — current holdings, one row per ticker per user."""

from __future__ import annotations

import sqlite3
from uuid import uuid4

from .connection import get_connection
from .util import now_iso


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "ticker": row["ticker"],
        "quantity": row["quantity"],
        "avg_cost": row["avg_cost"],
        "updated_at": row["updated_at"],
    }


def list_positions(user_id: str = "default") -> list[dict]:
    """Return all open positions for the user, ordered by ticker."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions "
            "WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]


def get_position(ticker: str, user_id: str = "default") -> dict | None:
    """Return a single position, or None if the user holds no shares of it."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions "
            "WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        return _row_to_dict(row) if row else None


def upsert_position(ticker: str, quantity: float, avg_cost: float, user_id: str = "default") -> None:
    """Create or replace the position row for a ticker.

    Callers (portfolio_service) own the avg_cost math; this just persists the
    resulting (quantity, avg_cost) pair. `avg_cost` is rounded to cents.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id, ticker) DO UPDATE SET
                quantity = excluded.quantity,
                avg_cost = excluded.avg_cost,
                updated_at = excluded.updated_at
            """,
            (str(uuid4()), user_id, ticker, quantity, round(avg_cost, 2), now_iso()),
        )


def delete_position(ticker: str, user_id: str = "default") -> None:
    """Delete the position row for a ticker (called when quantity reaches 0)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker))
