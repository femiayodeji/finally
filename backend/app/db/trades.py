"""Repository for `trades` — append-only trade execution log."""

from __future__ import annotations

from uuid import uuid4

from .connection import get_connection
from .util import now_iso


def insert_trade(
    ticker: str, side: str, quantity: float, price: float, user_id: str = "default"
) -> dict:
    """Insert a trade record and return the full row, including id and executed_at.

    `price` is rounded to cents (PLAN §8's money-precision rule); `quantity` is
    stored as given since fractional shares are supported.
    """
    trade_id = str(uuid4())
    executed_at = now_iso()
    rounded_price = round(price, 2)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, user_id, ticker, side, quantity, rounded_price, executed_at),
        )
    return {
        "id": trade_id,
        "user_id": user_id,
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": rounded_price,
        "executed_at": executed_at,
    }


def list_trades(limit: int = 100, user_id: str = "default") -> list[dict]:
    """Return the user's most recent trades, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, user_id, ticker, side, quantity, price, executed_at FROM trades "
            "WHERE user_id = ? ORDER BY executed_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
