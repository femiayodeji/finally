"""Tests for portfolio_service: valuation math and trade execution semantics."""

from __future__ import annotations

import pytest

from app import db
from app.services import TradeError, execute_trade, get_portfolio, snapshot_portfolio


class TestGetPortfolio:
    def test_empty_positions(self, cache):
        portfolio = get_portfolio(cache)
        assert portfolio["cash_balance"] == 10000.0
        assert portfolio["positions_value"] == 0.0
        assert portfolio["total_value"] == 10000.0
        assert portfolio["total_unrealized_pnl"] == 0.0
        assert portfolio["positions"] == []

    def test_position_valuation(self, cache):
        db.upsert_position("AAPL", 10, 190.0)
        cache.update("AAPL", 192.5)

        portfolio = get_portfolio(cache)
        assert portfolio["positions_value"] == 1925.0
        assert portfolio["total_unrealized_pnl"] == 25.0
        assert portfolio["total_value"] == 10000.0 + 1925.0

        [position] = portfolio["positions"]
        assert position["ticker"] == "AAPL"
        assert position["quantity"] == 10
        assert position["avg_cost"] == 190.0
        assert position["current_price"] == 192.5
        assert position["market_value"] == 1925.0
        assert position["unrealized_pnl"] == 25.0
        assert position["unrealized_pnl_percent"] == pytest.approx(1.32, abs=0.01)

    def test_position_without_cached_price_falls_back_to_avg_cost(self, cache):
        db.upsert_position("ZZZZ", 5, 100.0)

        portfolio = get_portfolio(cache)
        [position] = portfolio["positions"]
        assert position["current_price"] == 100.0
        assert position["unrealized_pnl"] == 0.0


class TestSnapshotPortfolio:
    def test_snapshot_persists_total_value(self, cache):
        total = snapshot_portfolio(cache)
        assert total == 10000.0
        [snapshot] = db.list_snapshots()
        assert snapshot["total_value"] == 10000.0


class TestExecuteTrade:
    async def test_buy_deducts_cash_and_opens_position(self, cache, source):
        cache.update("AAPL", 190.0)

        result = await execute_trade(cache, source, "AAPL", "buy", 10)

        assert result["trade"]["ticker"] == "AAPL"
        assert result["trade"]["side"] == "buy"
        assert result["trade"]["price"] == 190.0
        assert db.get_cash_balance() == 10000.0 - 1900.0
        position = db.get_position("AAPL")
        assert position["quantity"] == 10
        assert position["avg_cost"] == 190.0
        assert "AAPL" in source.tickers

    async def test_buy_weighted_average_cost(self, cache, source):
        cache.update("AAPL", 100.0)
        await execute_trade(cache, source, "AAPL", "buy", 10)  # 10 @ 100 = 1000
        cache.update("AAPL", 200.0)
        await execute_trade(cache, source, "AAPL", "buy", 10)  # 10 @ 200 = 2000

        position = db.get_position("AAPL")
        assert position["quantity"] == 20
        assert position["avg_cost"] == pytest.approx(150.0)

    async def test_buy_insufficient_cash_raises_and_changes_nothing(self, cache, source):
        cache.update("AAPL", 190.0)

        with pytest.raises(TradeError):
            await execute_trade(cache, source, "AAPL", "buy", 1000)

        assert db.get_cash_balance() == 10000.0
        assert db.get_position("AAPL") is None
        assert db.list_trades() == []

    async def test_sell_increases_cash_and_unchanged_avg_cost(self, cache, source):
        cache.update("AAPL", 100.0)
        await execute_trade(cache, source, "AAPL", "buy", 10)

        cache.update("AAPL", 150.0)
        result = await execute_trade(cache, source, "AAPL", "sell", 4)

        assert result["trade"]["side"] == "sell"
        position = db.get_position("AAPL")
        assert position["quantity"] == 6
        assert position["avg_cost"] == 100.0  # unchanged on sell
        assert db.get_cash_balance() == 10000.0 - 1000.0 + 600.0

    async def test_sell_all_closes_position_row(self, cache, source):
        cache.update("AAPL", 100.0)
        await execute_trade(cache, source, "AAPL", "buy", 10)

        await execute_trade(cache, source, "AAPL", "sell", 10)

        assert db.get_position("AAPL") is None

    async def test_sell_all_stops_tracking_when_not_watchlisted(self, cache, source):
        cache.update("ZZZZ", 50.0)
        await execute_trade(cache, source, "ZZZZ", "buy", 2)
        assert "ZZZZ" in source.tickers

        await execute_trade(cache, source, "ZZZZ", "sell", 2)
        assert "ZZZZ" not in source.tickers

    async def test_sell_all_keeps_tracking_when_watchlisted(self, cache, source):
        db.add_watchlist("AAPL")
        cache.update("AAPL", 100.0)
        await execute_trade(cache, source, "AAPL", "buy", 2)

        await execute_trade(cache, source, "AAPL", "sell", 2)
        assert "AAPL" in source.tickers

    async def test_sell_insufficient_shares_raises_and_changes_nothing(self, cache, source):
        cache.update("AAPL", 100.0)
        await execute_trade(cache, source, "AAPL", "buy", 5)

        with pytest.raises(TradeError):
            await execute_trade(cache, source, "AAPL", "sell", 100)

        assert db.get_position("AAPL")["quantity"] == 5

    async def test_sell_without_position_raises(self, cache, source):
        cache.update("AAPL", 100.0)
        with pytest.raises(TradeError):
            await execute_trade(cache, source, "AAPL", "sell", 1)

    async def test_no_cached_price_raises(self, cache, source):
        with pytest.raises(TradeError):
            await execute_trade(cache, source, "NOPE", "buy", 1)

    async def test_invalid_side_raises(self, cache, source):
        cache.update("AAPL", 100.0)
        with pytest.raises(TradeError):
            await execute_trade(cache, source, "AAPL", "hold", 1)

    async def test_non_positive_quantity_raises(self, cache, source):
        cache.update("AAPL", 100.0)
        with pytest.raises(TradeError):
            await execute_trade(cache, source, "AAPL", "buy", 0)
        with pytest.raises(TradeError):
            await execute_trade(cache, source, "AAPL", "buy", -5)

    async def test_money_rounded_to_cents(self, cache, source):
        cache.update("AAPL", 33.333)  # cache itself rounds to 33.33
        result = await execute_trade(cache, source, "AAPL", "buy", 3)
        assert result["trade"]["price"] == 33.33
        assert db.get_cash_balance() == round(10000.0 - 3 * 33.33, 2)

    async def test_trade_writes_snapshot(self, cache, source):
        cache.update("AAPL", 100.0)
        await execute_trade(cache, source, "AAPL", "buy", 1)
        assert len(db.list_snapshots()) == 1
