"""Tests for the watchlist repo + service (PLAN.md §6 Tracked Ticker Set, §8
Watchlist Validation). Route-level tests for `/api/watchlist` are added in
Task 2 once the router exists.
"""

from __future__ import annotations

import pytest

from app.db import database, watchlist_repo
from app.market.cache import PriceCache
from app.market.simulator import SimulatorDataSource
from app.services import watchlist_service


@pytest.fixture()
def tmp_db_path(tmp_path, monkeypatch):
    """Point DB_PATH at a tmp file and initialize a fresh, hermetic schema."""
    db_path = tmp_path / "finally_test.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_path))
    database.initialize()
    return db_path


class FakeMarketDataSource:
    """Minimal MarketDataSource stub capturing add/remove calls.

    Deliberately NOT a `SimulatorDataSource` subclass, so
    `watchlist_service.add()` exercises the Massive-mode
    priced/unpriceable-rejection branch when `priceable=False`.
    """

    def __init__(self, cache: PriceCache, priceable: bool = True) -> None:
        self._cache = cache
        self._priceable = priceable
        self.added: list[str] = []
        self.removed: list[str] = []

    async def start(self, tickers: list[str]) -> None:  # pragma: no cover - unused in tests
        pass

    async def stop(self) -> None:  # pragma: no cover - unused in tests
        pass

    async def add_ticker(self, ticker: str) -> None:
        self.added.append(ticker)
        if self._priceable:
            self._cache.update(ticker=ticker, price=100.0)

    async def remove_ticker(self, ticker: str) -> None:
        self.removed.append(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:  # pragma: no cover - unused in tests
        return []


class TestValidateSymbol:
    """watchlist_service.validate_symbol()."""

    def test_normalizes_lowercase_to_uppercase(self):
        assert watchlist_service.validate_symbol("aapl") == "AAPL"

    def test_accepts_single_letter(self):
        assert watchlist_service.validate_symbol("v") == "V"

    def test_accepts_five_letters(self):
        assert watchlist_service.validate_symbol("googl") == "GOOGL"

    def test_rejects_more_than_five_letters(self):
        with pytest.raises(ValueError):
            watchlist_service.validate_symbol("TOOLONG")

    def test_rejects_digits(self):
        with pytest.raises(ValueError):
            watchlist_service.validate_symbol("12")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError):
            watchlist_service.validate_symbol("")


class TestWatchlistRepoIdempotency:
    """watchlist_repo.add_ticker() duplicate handling (WATCH-02)."""

    def test_duplicate_add_is_idempotent(self, tmp_db_path):
        watchlist_repo.add_ticker("PYPL")
        watchlist_repo.add_ticker("PYPL")

        tickers = watchlist_repo.list_tickers()
        assert tickers.count("PYPL") == 1

    def test_has_open_position_false_when_no_position(self, tmp_db_path):
        assert watchlist_repo.has_open_position("PYPL") is False

    def test_has_open_position_true_when_position_exists(self, tmp_db_path):
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
                VALUES ('pos-1', 'default', 'PYPL', 5.0, 60.0, '2026-01-01T00:00:00+00:00')
                """
            )

        assert watchlist_repo.has_open_position("PYPL") is True


class TestServiceAdd:
    """watchlist_service.add() — validation, persistence, tracked-set sync."""

    async def test_add_persists_and_tracks(self, tmp_db_path):
        cache = PriceCache()
        source = FakeMarketDataSource(cache)

        ticker = await watchlist_service.add(cache, source, "pypl")

        assert ticker == "PYPL"
        assert "PYPL" in watchlist_repo.list_tickers()
        assert source.added == ["PYPL"]

    async def test_add_invalid_symbol_raises_and_does_not_persist(self, tmp_db_path):
        cache = PriceCache()
        source = FakeMarketDataSource(cache)

        with pytest.raises(ValueError):
            await watchlist_service.add(cache, source, "TOOLONG")

        assert "TOOLONG" not in watchlist_repo.list_tickers()
        assert source.added == []

    async def test_simulator_mode_accepts_any_well_formed_symbol(self, tmp_db_path):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start([])

        ticker = await watchlist_service.add(cache, source, "zzzz")

        assert ticker == "ZZZZ"
        assert cache.get("ZZZZ") is not None

        await source.stop()

    async def test_massive_mode_rejects_unpriceable_symbol(self, tmp_db_path, monkeypatch):
        # Shrink the poll-retry window so this test stays fast.
        monkeypatch.setattr(watchlist_service, "_MASSIVE_ADD_RETRIES", 2)
        monkeypatch.setattr(watchlist_service, "_MASSIVE_ADD_POLL_INTERVAL", 0.01)
        cache = PriceCache()
        source = FakeMarketDataSource(cache, priceable=False)

        with pytest.raises(ValueError):
            await watchlist_service.add(cache, source, "ZZZZ")

        assert "ZZZZ" not in watchlist_repo.list_tickers()
        assert source.removed == ["ZZZZ"]


class TestServiceRemove:
    """watchlist_service.remove() — tracked-set-keeps-position rule (MKT-05)."""

    async def test_remove_untracks_when_no_open_position(self, tmp_db_path):
        cache = PriceCache()
        source = FakeMarketDataSource(cache)
        await watchlist_service.add(cache, source, "PYPL")

        ticker = await watchlist_service.remove(cache, source, "pypl")

        assert ticker == "PYPL"
        assert "PYPL" not in watchlist_repo.list_tickers()
        assert source.removed == ["PYPL"]

    async def test_remove_keeps_tracking_when_position_open(self, tmp_db_path, monkeypatch):
        cache = PriceCache()
        source = FakeMarketDataSource(cache)
        await watchlist_service.add(cache, source, "PYPL")

        monkeypatch.setattr(watchlist_repo, "has_open_position", lambda *a, **k: True)

        ticker = await watchlist_service.remove(cache, source, "PYPL")

        assert ticker == "PYPL"
        assert "PYPL" not in watchlist_repo.list_tickers()  # DB row is still removed
        assert source.removed == []  # but tracking is NOT stopped


class TestListWatchlist:
    """watchlist_service.list_watchlist() — WatchlistEntry shape (WATCH-01)."""

    def test_shape_without_cache_tick(self, tmp_db_path):
        # database.initialize() (via tmp_db_path) already seeds AAPL as part
        # of the default 10-ticker watchlist (PLAN.md §7) — assert against
        # that entry's shape rather than assuming it's the only row.
        cache = PriceCache()

        entries = watchlist_service.list_watchlist(cache)
        aapl = next(e for e in entries if e["ticker"] == "AAPL")

        assert aapl == {
            "ticker": "AAPL",
            "price": None,
            "previous_price": None,
            "change": None,
            "session_change_percent": None,
            "direction": None,
            "timestamp": None,
        }

    def test_shape_with_cache_tick(self, tmp_db_path):
        # AAPL is already seeded by database.initialize() (see above).
        cache = PriceCache()
        cache.update(ticker="AAPL", price=190.0)

        entries = watchlist_service.list_watchlist(cache)
        aapl = next(e for e in entries if e["ticker"] == "AAPL")

        assert aapl["price"] == 190.0
        assert aapl["direction"] == "flat"
        assert aapl["session_change_percent"] == 0.0
