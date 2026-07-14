"""Tests for the positions repository."""

from __future__ import annotations

from app.db import delete_position, get_position, list_positions, upsert_position


class TestPositionsRepository:
    """Unit tests for position upsert/get/list/delete."""

    def test_get_position_missing_returns_none(self):
        """Test get_position() for a ticker never bought returns None."""
        assert get_position("AAPL") is None

    def test_upsert_creates_position(self):
        """Test upserting a new ticker creates a row."""
        upsert_position("AAPL", quantity=10, avg_cost=190.1234)
        position = get_position("AAPL")
        assert position["ticker"] == "AAPL"
        assert position["quantity"] == 10
        assert position["avg_cost"] == 190.12  # rounded to cents

    def test_upsert_replaces_existing_position(self):
        """Test upserting the same ticker again updates quantity/avg_cost in place."""
        upsert_position("AAPL", quantity=10, avg_cost=190.0)
        upsert_position("AAPL", quantity=15, avg_cost=192.5)
        position = get_position("AAPL")
        assert position["quantity"] == 15
        assert position["avg_cost"] == 192.5
        assert len(list_positions()) == 1  # UNIQUE(user_id, ticker) — one row, not two

    def test_list_positions_ordered_by_ticker(self):
        """Test list_positions() returns all open positions, alphabetically."""
        upsert_position("TSLA", quantity=1, avg_cost=200.0)
        upsert_position("AAPL", quantity=1, avg_cost=190.0)
        tickers = [p["ticker"] for p in list_positions()]
        assert tickers == ["AAPL", "TSLA"]

    def test_delete_position(self):
        """Test deleting a position removes its row (called when quantity hits 0)."""
        upsert_position("AAPL", quantity=10, avg_cost=190.0)
        delete_position("AAPL")
        assert get_position("AAPL") is None
        assert list_positions() == []

    def test_delete_nonexistent_position_does_not_raise(self):
        """Test deleting a ticker with no open position is a silent no-op."""
        delete_position("NOPE")  # Should not raise
