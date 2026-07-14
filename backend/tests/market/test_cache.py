"""Tests for PriceCache."""

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

    def test_session_reference_captured_on_first_update(self):
        """Test the session reference is set from the first observation."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.00)
        assert update.session_reference == 190.00

    def test_session_reference_stable_across_updates(self):
        """Test the session reference is never overwritten by later updates."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        second = cache.update("AAPL", 195.00)
        third = cache.update("AAPL", 180.00)
        assert second.session_reference == 190.00
        assert third.session_reference == 190.00

    def test_session_change_percent_threaded_through_update(self):
        """Test update() constructs PriceUpdate with a populated session_reference
        so session_change_percent is server-computed."""
        cache = PriceCache()
        cache.update("AAPL", 100.00)
        update = cache.update("AAPL", 110.00)
        assert update.session_change_percent == 10.0

    def test_history_grows_with_updates(self):
        """Test the rolling history buffer accumulates points."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("AAPL", 191.00)
        cache.update("AAPL", 192.00)
        history = cache.get_history("AAPL")
        assert len(history) == 3
        assert history[0]["price"] == 190.00
        assert history[-1]["price"] == 192.00
        assert all("timestamp" in point and "price" in point for point in history)

    def test_history_bounded_with_fifo_eviction(self):
        """Test history is capped at MAX_HISTORY_POINTS with oldest evicted first."""
        cache = PriceCache()
        for i in range(650):
            cache.update("AAPL", 100.00 + i, timestamp=float(i))
        history = cache.get_history("AAPL")
        assert len(history) == 600
        # Oldest 50 points (timestamps 0..49) should have been evicted.
        assert history[0]["timestamp"] == 50.0
        assert history[-1]["timestamp"] == 649.0

    def test_get_history_unknown_ticker(self):
        """Test get_history returns an empty list for an unknown ticker."""
        cache = PriceCache()
        assert cache.get_history("NOPE") == []

    def test_get_history_returns_copy(self):
        """Test get_history returns a copy that callers cannot use to mutate internal state."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        history = cache.get_history("AAPL")
        history.append({"timestamp": 0.0, "price": 0.0})
        assert len(cache.get_history("AAPL")) == 1

    def test_remove_clears_session_reference_and_history(self):
        """Test remove() clears price, session reference, and history for the ticker."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("AAPL", 191.00)
        cache.remove("AAPL")
        assert cache.get("AAPL") is None
        assert cache.get_history("AAPL") == []
        # Re-adding should capture a fresh session reference, proving the old one was cleared.
        update = cache.update("AAPL", 200.00)
        assert update.session_reference == 200.00
