"""Repository for `users_profile` — cash balance for the (currently single) user."""

from __future__ import annotations

from .connection import get_connection


def get_cash_balance(user_id: str = "default") -> float:
    """Return the user's current cash balance. 0.0 if the user row doesn't exist."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
        return row["cash_balance"] if row else 0.0


def set_cash_balance(value: float, user_id: str = "default") -> None:
    """Set the user's cash balance, rounded to cents."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (round(value, 2), user_id),
        )
