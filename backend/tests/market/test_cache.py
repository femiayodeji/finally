"""Tests for PriceCache."""

import pytest

from app.market.cache import PriceCache


class TestPriceCache:
    """Unit tests for the PriceCache."""

    def test_update_and_get(self):
        """Test updating and getting a price."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.ticker == "AAPL"
        assert update.price == 190.50
        assert cache.get("AAPL") == update

    def test_first_update_is_flat(self):
        """Test that the first update has flat direction."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.direction == "flat"
        assert update.previous_price == 190.50

    def test_direction_up(self):
        """Test price update with upward direction."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 191.00)
        assert update.direction == "up"
        assert update.change == 1.00

    def test_direction_down(self):
        """Test price update with downward direction."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 189.00)
        assert update.direction == "down"
        assert update.change == -1.00

    def test_remove(self):
        """Test removing a ticker from cache."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.remove("AAPL")
        assert cache.get("AAPL") is None

    def test_remove_nonexistent(self):
        """Test removing a ticker that doesn't exist."""
        cache = PriceCache()
        cache.remove("AAPL")  # Should not raise

    def test_get_all(self):
        """Test getting all prices."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("GOOGL", 175.00)
        all_prices = cache.get_all()
        assert set(all_prices.keys()) == {"AAPL", "GOOGL"}

    def test_version_increments(self):
        """Test that version counter increments."""
        cache = PriceCache()
        v0 = cache.version
        cache.update("AAPL", 190.00)
        assert cache.version == v0 + 1
        cache.update("AAPL", 191.00)
        assert cache.version == v0 + 2

    def test_get_price_convenience(self):
        """Test the convenience get_price method."""
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        assert cache.get_price("AAPL") == 190.50
        assert cache.get_price("NOPE") is None

    def test_len(self):
        """Test __len__ method."""
        cache = PriceCache()
        assert len(cache) == 0
        cache.update("AAPL", 190.00)
        assert len(cache) == 1
        cache.update("GOOGL", 175.00)
        assert len(cache) == 2

    def test_contains(self):
        """Test __contains__ method."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        assert "AAPL" in cache
        assert "GOOGL" not in cache

    def test_custom_timestamp(self):
        """Test updating with a custom timestamp."""
        cache = PriceCache()
        custom_ts = 1234567890.0
        update = cache.update("AAPL", 190.50, timestamp=custom_ts)
        assert update.timestamp == custom_ts

    def test_price_rounding(self):
        """Test that prices are rounded to 2 decimal places."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.12345)
        assert update.price == 190.12

    def test_session_reference_set_on_first_update(self):
        """First update for a ticker becomes its session reference price."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.00)
        assert update.session_reference == 190.00

    def test_session_reference_stable_across_updates(self):
        """Session reference doesn't move on subsequent ticks."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 195.00)
        assert update.session_reference == 190.00
        assert update.session_change_percent == pytest.approx(2.6316, abs=0.001)

    def test_remove_clears_session_reference_and_history(self):
        """Removing a ticker resets session reference + history (fresh on re-add)."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.remove("AAPL")
        update = cache.update("AAPL", 200.00)
        assert update.session_reference == 200.00
        assert cache.get_history("AAPL") == [{"timestamp": update.timestamp, "price": 200.00}]

    def test_get_history_empty_for_unknown_ticker(self):
        """get_history returns [] for a ticker with no recorded ticks."""
        cache = PriceCache()
        assert cache.get_history("NOPE") == []

    def test_get_history_accumulates_in_order(self):
        """get_history returns (timestamp, price) points oldest first."""
        cache = PriceCache()
        cache.update("AAPL", 190.00, timestamp=1.0)
        cache.update("AAPL", 191.00, timestamp=2.0)
        assert cache.get_history("AAPL") == [
            {"timestamp": 1.0, "price": 190.00},
            {"timestamp": 2.0, "price": 191.00},
        ]

    def test_get_history_bounded_by_maxlen(self):
        """History is a ring buffer — oldest points fall off past HISTORY_MAXLEN."""
        from app.market.cache import HISTORY_MAXLEN

        cache = PriceCache()
        for i in range(HISTORY_MAXLEN + 10):
            cache.update("AAPL", 100.0 + i, timestamp=float(i))
        history = cache.get_history("AAPL")
        assert len(history) == HISTORY_MAXLEN
        assert history[0]["timestamp"] == 10.0
        assert history[-1]["timestamp"] == float(HISTORY_MAXLEN + 9)
