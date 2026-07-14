"""Tests for PriceUpdate dataclass."""

import pytest

from app.market.models import PriceUpdate


class TestPriceUpdate:
    """Unit tests for the PriceUpdate model."""

    def test_price_update_creation(self):
        """Test basic PriceUpdate creation."""
        update = PriceUpdate(ticker="AAPL", price=190.50, previous_price=190.00, timestamp=1234567890.0)
        assert update.ticker == "AAPL"
        assert update.price == 190.50
        assert update.previous_price == 190.00
        assert update.timestamp == 1234567890.0

    def test_change_calculation(self):
        """Test price change calculation."""
        update = PriceUpdate(ticker="AAPL", price=190.50, previous_price=190.00, timestamp=1234567890.0)
        assert update.change == 0.50

    def test_change_negative(self):
        """Test negative price change."""
        update = PriceUpdate(ticker="AAPL", price=189.50, previous_price=190.00, timestamp=1234567890.0)
        assert update.change == -0.50

    def test_change_percent_up(self):
        """Test percentage change calculation (up)."""
        update = PriceUpdate(ticker="AAPL", price=190.00, previous_price=100.00, timestamp=1234567890.0)
        assert update.change_percent == 90.0

    def test_change_percent_down(self):
        """Test percentage change calculation (down)."""
        update = PriceUpdate(ticker="AAPL", price=100.00, previous_price=200.00, timestamp=1234567890.0)
        assert update.change_percent == -50.0

    def test_change_percent_zero_previous(self):
        """Test percentage change with zero previous price."""
        update = PriceUpdate(ticker="AAPL", price=100.00, previous_price=0.00, timestamp=1234567890.0)
        assert update.change_percent == 0.0

    def test_direction_up(self):
        """Test direction calculation (up)."""
        update = PriceUpdate(ticker="AAPL", price=191.00, previous_price=190.00, timestamp=1234567890.0)
        assert update.direction == "up"

    def test_direction_down(self):
        """Test direction calculation (down)."""
        update = PriceUpdate(ticker="AAPL", price=189.00, previous_price=190.00, timestamp=1234567890.0)
        assert update.direction == "down"

    def test_direction_flat(self):
        """Test direction calculation (flat)."""
        update = PriceUpdate(ticker="AAPL", price=190.00, previous_price=190.00, timestamp=1234567890.0)
        assert update.direction == "flat"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        update = PriceUpdate(ticker="AAPL", price=190.50, previous_price=190.00, timestamp=1234567890.0)
        result = update.to_dict()

        assert result["ticker"] == "AAPL"
        assert result["price"] == 190.50
        assert result["previous_price"] == 190.00
        assert result["timestamp"] == 1234567890.0
        assert result["change"] == 0.50
        assert result["change_percent"] == 0.2632  # (0.50 / 190.00) * 100
        assert result["direction"] == "up"

    def test_session_change_percent_positive(self):
        """Test session_change_percent when price is above the session reference."""
        update = PriceUpdate(
            ticker="AAPL",
            price=110.00,
            previous_price=105.00,
            timestamp=1234567890.0,
            session_reference=100.00,
        )
        assert update.session_change_percent == 10.0

    def test_session_change_percent_negative(self):
        """Test session_change_percent when price is below the session reference."""
        update = PriceUpdate(
            ticker="AAPL",
            price=90.00,
            previous_price=95.00,
            timestamp=1234567890.0,
            session_reference=100.00,
        )
        assert update.session_change_percent == -10.0

    def test_session_change_percent_first_tick_zero(self):
        """Test session_change_percent is 0.0 on the first observation (no reference set)."""
        update = PriceUpdate(ticker="AAPL", price=190.50, previous_price=190.50, timestamp=1234567890.0)
        assert update.session_reference is None
        assert update.session_change_percent == 0.0

    def test_session_change_percent_zero_reference(self):
        """Test session_change_percent falls back to 0.0 when reference is exactly 0."""
        update = PriceUpdate(
            ticker="AAPL",
            price=100.00,
            previous_price=100.00,
            timestamp=1234567890.0,
            session_reference=0.0,
        )
        assert update.session_change_percent == 0.0

    def test_to_dict_includes_session_change_percent(self):
        """Test to_dict() is a strict superset — adds session_change_percent, keeps prior keys."""
        update = PriceUpdate(
            ticker="AAPL",
            price=110.00,
            previous_price=105.00,
            timestamp=1234567890.0,
            session_reference=100.00,
        )
        result = update.to_dict()

        assert result["session_change_percent"] == 10.0
        # Strict superset: every pre-existing key is still present.
        for key in ("ticker", "price", "previous_price", "timestamp", "change", "change_percent", "direction"):
            assert key in result

    def test_immutability(self):
        """Test that PriceUpdate is immutable."""
        update = PriceUpdate(ticker="AAPL", price=190.50, previous_price=190.00, timestamp=1234567890.0)

        with pytest.raises(AttributeError):
            update.price = 200.00  # Should raise error
