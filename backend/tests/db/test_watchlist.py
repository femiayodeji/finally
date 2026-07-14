"""Tests for the watchlist repository."""

from __future__ import annotations

from app.db import add_watchlist, is_watchlisted, list_watchlist, remove_watchlist
from app.db.init_db import DEFAULT_WATCHLIST


class TestWatchlistRepository:
    """Unit tests for watchlist CRUD."""

    def test_list_watchlist_returns_seeded_tickers(self):
        """Test the seeded default watchlist is returned in insertion order."""
        assert list_watchlist() == DEFAULT_WATCHLIST

    def test_add_new_ticker(self):
        """Test adding a ticker not already present."""
        added = add_watchlist("PYPL")
        assert added is True
        assert "PYPL" in list_watchlist()

    def test_add_ticker_is_idempotent(self):
        """Test adding an already-watchlisted ticker is a no-op, returns False."""
        add_watchlist("PYPL")
        added_again = add_watchlist("PYPL")
        assert added_again is False
        assert list_watchlist().count("PYPL") == 1

    def test_remove_ticker(self):
        """Test removing a watchlisted ticker."""
        remove_watchlist("AAPL")
        assert "AAPL" not in list_watchlist()

    def test_remove_nonexistent_ticker_does_not_raise(self):
        """Test removing a ticker never on the watchlist is a silent no-op."""
        remove_watchlist("NOPE")  # Should not raise

    def test_is_watchlisted_true(self):
        """Test is_watchlisted() for a present ticker."""
        assert is_watchlisted("AAPL") is True

    def test_is_watchlisted_false(self):
        """Test is_watchlisted() for an absent ticker."""
        assert is_watchlisted("NOPE") is False

    def test_watchlist_scoped_per_user(self):
        """Test a different user_id has its own independent watchlist."""
        add_watchlist("PYPL", user_id="alice")
        assert list_watchlist(user_id="alice") == ["PYPL"]
        assert "PYPL" not in list_watchlist()
