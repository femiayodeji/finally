"""Tests for watchlist_service: validation and the tracked-set rule (PLAN §6)."""

from __future__ import annotations

import pytest

from app import db
from app.services import WatchlistError, add_to_watchlist, get_watchlist, remove_from_watchlist


class TestGetWatchlist:
    def test_lists_seeded_tickers_with_null_price_until_ticked(self, cache):
        watchlist = get_watchlist(cache)
        tickers = {entry["ticker"] for entry in watchlist}
        assert tickers == {"AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"}
        assert all(entry["price"] is None for entry in watchlist)

    def test_reflects_cached_price(self, cache):
        cache.update("AAPL", 192.5)
        watchlist = get_watchlist(cache)
        aapl = next(e for e in watchlist if e["ticker"] == "AAPL")
        assert aapl["price"] == 192.5
        assert aapl["direction"] == "flat"


class TestAddToWatchlist:
    async def test_adds_and_tracks(self, cache, source):
        result = await add_to_watchlist(cache, source, "pypl")
        assert result == {"ticker": "PYPL"}
        assert db.is_watchlisted("PYPL")
        assert "PYPL" in source.tickers

    async def test_idempotent(self, cache, source):
        await add_to_watchlist(cache, source, "PYPL")
        await add_to_watchlist(cache, source, "PYPL")
        assert db.list_watchlist().count("PYPL") == 1

    @pytest.mark.parametrize("bad", ["", "TOOLONG", "ab1", "AB-C", "123"])
    async def test_rejects_malformed_symbol(self, cache, source, bad):
        with pytest.raises(WatchlistError):
            await add_to_watchlist(cache, source, bad)
        assert not db.is_watchlisted(bad.upper())


class TestRemoveFromWatchlist:
    async def test_removes_and_stops_tracking_without_position(self, cache, source):
        await add_to_watchlist(cache, source, "PYPL")
        await remove_from_watchlist(cache, source, "PYPL")
        assert not db.is_watchlisted("PYPL")
        assert "PYPL" not in source.tickers

    async def test_keeps_tracking_when_open_position_remains(self, cache, source):
        await add_to_watchlist(cache, source, "AAPL")
        db.upsert_position("AAPL", 5, 100.0)

        await remove_from_watchlist(cache, source, "AAPL")

        assert not db.is_watchlisted("AAPL")
        assert "AAPL" in source.tickers  # position still open
