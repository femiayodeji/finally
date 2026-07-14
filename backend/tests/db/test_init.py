"""Tests for init_db() — schema creation and default-data seeding."""

from __future__ import annotations

from app.db import get_cash_balance, list_watchlist
from app.db.connection import get_connection
from app.db.init_db import DEFAULT_CASH_BALANCE, DEFAULT_WATCHLIST, init_db


class TestInitDb:
    """Unit tests for init_db()."""

    def test_seeds_default_cash_balance(self):
        """Test the default user is seeded with $10,000 cash."""
        assert get_cash_balance() == DEFAULT_CASH_BALANCE

    def test_seeds_default_watchlist(self):
        """Test the default 10 tickers are seeded."""
        assert list_watchlist() == DEFAULT_WATCHLIST

    def test_creates_all_six_tables(self):
        """Test all six tables from PLAN §7 exist after init."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            table_names = {row["name"] for row in rows}
        expected = {
            "users_profile",
            "watchlist",
            "positions",
            "trades",
            "portfolio_snapshots",
            "chat_messages",
        }
        assert expected <= table_names

    def test_idempotent_does_not_duplicate_seed_data(self):
        """Test calling init_db() again doesn't re-seed or error."""
        init_db()
        init_db()
        assert get_cash_balance() == DEFAULT_CASH_BALANCE
        assert list_watchlist() == DEFAULT_WATCHLIST

    def test_idempotent_preserves_user_changes(self):
        """Test re-running init_db() doesn't clobber data written after the first init."""
        from app.db import set_cash_balance

        set_cash_balance(12345.67)
        init_db()
        assert get_cash_balance() == 12345.67
