"""Fixtures for service-layer tests — temp DB + a fake market data source."""

from __future__ import annotations

import pytest

from app.db import init_db
from app.market import MarketDataSource, PriceCache


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Point FINALLY_DB_PATH at a fresh temp file and initialize (schema + seed)."""
    db_file = tmp_path / "test_finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_file))
    init_db()
    return db_file


class FakeMarketSource(MarketDataSource):
    """In-memory stand-in for SimulatorDataSource/MassiveDataSource.

    Just records which tickers are tracked so tests can assert on the
    tracked-set behavior (PLAN §6) without spinning up a real background task.
    """

    def __init__(self) -> None:
        self.tickers: set[str] = set()
        self.started_with: list[str] | None = None

    async def start(self, tickers: list[str]) -> None:
        self.started_with = list(tickers)
        self.tickers = set(tickers)

    async def stop(self) -> None:
        pass

    async def add_ticker(self, ticker: str) -> None:
        self.tickers.add(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self.tickers.discard(ticker)

    def get_tickers(self) -> list[str]:
        return sorted(self.tickers)


@pytest.fixture
def cache() -> PriceCache:
    return PriceCache()


@pytest.fixture
def source() -> FakeMarketSource:
    return FakeMarketSource()
