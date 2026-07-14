"""Tests for the SQLite persistence layer (schema init, seed, idempotency)."""

from __future__ import annotations

import sqlite3

import pytest

from app.db import database
from app.market.seed_prices import SEED_PRICES

EXPECTED_TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


@pytest.fixture()
def tmp_db_path(tmp_path, monkeypatch):
    """Point DB_PATH at a tmp file so tests are hermetic (DB-03 persistence semantics)."""
    db_path = tmp_path / "finally_test.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_path))
    return db_path


class TestInitialize:
    """Tests for database.initialize() — schema creation + seeding."""

    def test_creates_all_six_tables(self, tmp_db_path):
        database.initialize()

        with sqlite3.connect(tmp_db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        table_names = {row[0] for row in rows}

        assert EXPECTED_TABLES.issubset(table_names)

    def test_seeds_one_default_user_with_10000_cash(self, tmp_db_path):
        database.initialize()

        with database.get_connection() as conn:
            rows = conn.execute("SELECT * FROM users_profile").fetchall()

        assert len(rows) == 1
        assert rows[0]["id"] == "default"
        assert rows[0]["cash_balance"] == 10000.0

    def test_seeds_10_watchlist_tickers_matching_seed_set(self, tmp_db_path):
        database.initialize()

        with database.get_connection() as conn:
            rows = conn.execute("SELECT ticker FROM watchlist").fetchall()

        tickers = {row["ticker"] for row in rows}
        assert len(rows) == 10
        assert tickers == set(SEED_PRICES.keys())

    def test_file_persists_at_tmp_path(self, tmp_db_path):
        database.initialize()

        assert tmp_db_path.exists()

    def test_idempotent_second_call_changes_nothing(self, tmp_db_path):
        database.initialize()
        database.initialize()

        with database.get_connection() as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
            watchlist_count = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]

        assert user_count == 1
        assert watchlist_count == 10

    def test_idempotent_does_not_raise(self, tmp_db_path):
        database.initialize()
        database.initialize()  # must not raise


class TestGetTrackedTickers:
    """Tests for database.get_tracked_tickers() — watchlist ∪ open positions."""

    def test_returns_watchlist_when_no_positions(self, tmp_db_path):
        database.initialize()

        tracked = database.get_tracked_tickers()

        assert set(tracked) == set(SEED_PRICES.keys())

    def test_includes_open_position_not_on_watchlist(self, tmp_db_path):
        database.initialize()

        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
                VALUES ('pos-1', 'default', 'PYPL', 5.0, 60.0, '2026-01-01T00:00:00+00:00')
                """
            )

        tracked = database.get_tracked_tickers()

        assert "PYPL" in tracked
        assert set(SEED_PRICES.keys()).issubset(set(tracked))
