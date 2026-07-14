"""Tests for the users_profile repository."""

from __future__ import annotations

from app.db import get_cash_balance, set_cash_balance


class TestUsersRepository:
    """Unit tests for cash balance get/set."""

    def test_get_default_cash_balance(self):
        """Test the seeded default user starts with $10,000."""
        assert get_cash_balance() == 10000.0

    def test_set_and_get_cash_balance(self):
        """Test setting a new cash balance and reading it back."""
        set_cash_balance(9500.25)
        assert get_cash_balance() == 9500.25

    def test_set_cash_balance_rounds_to_cents(self):
        """Test cash balance is rounded to 2 decimal places on write."""
        set_cash_balance(9500.256789)
        assert get_cash_balance() == 9500.26

    def test_get_cash_balance_unknown_user(self):
        """Test an unseeded user_id returns 0.0 rather than raising."""
        assert get_cash_balance(user_id="nobody") == 0.0
