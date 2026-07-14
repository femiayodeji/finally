"""Repository for `portfolio_snapshots` — total portfolio value over time (P&L chart)."""

from __future__ import annotations

from uuid import uuid4

from .connection import get_connection
from .util import now_iso


def insert_snapshot(total_value: float, user_id: str = "default") -> None:
    """Record a portfolio value snapshot (30s background cadence + after each trade)."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (str(uuid4()), user_id, round(total_value, 2), now_iso()),
        )


def list_snapshots(limit: int = 500, user_id: str = "default") -> list[dict]:
    """Return up to `limit` most recent snapshots for the user, chronological (oldest first)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT total_value, recorded_at FROM (
                SELECT total_value, recorded_at FROM portfolio_snapshots
                WHERE user_id = ? ORDER BY recorded_at DESC LIMIT ?
            ) ORDER BY recorded_at ASC
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
