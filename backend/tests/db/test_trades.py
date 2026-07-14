"""Tests for the trades repository."""

from __future__ import annotations

import time

from app.db import insert_trade, list_trades


class TestTradesRepository:
    """Unit tests for the append-only trades log."""

    def test_insert_trade_returns_full_row(self):
        """Test insert_trade() returns id, executed_at, and the rounded price."""
        trade = insert_trade("AAPL", "buy", quantity=10, price=190.1234)
        assert trade["id"]
        assert trade["executed_at"]
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 10
        assert trade["price"] == 190.12  # rounded to cents

    def test_list_trades_newest_first(self):
        """Test list_trades() orders by executed_at, newest first."""
        first = insert_trade("AAPL", "buy", quantity=10, price=190.0)
        time.sleep(0.002)
        second = insert_trade("AAPL", "sell", quantity=5, price=192.0)
        trades = list_trades()
        assert [t["id"] for t in trades] == [second["id"], first["id"]]

    def test_list_trades_respects_limit(self):
        """Test list_trades() caps the result at `limit`."""
        for _ in range(5):
            insert_trade("AAPL", "buy", quantity=1, price=100.0)
            time.sleep(0.002)
        assert len(list_trades(limit=3)) == 3

    def test_trades_scoped_per_user(self):
        """Test trades are isolated per user_id."""
        insert_trade("AAPL", "buy", quantity=1, price=100.0, user_id="alice")
        assert list_trades() == []
        assert len(list_trades(user_id="alice")) == 1
