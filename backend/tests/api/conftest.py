"""Fixtures for API route tests — a minimal FastAPI app wired with real routers
against a temp DB, a real PriceCache, and a fake (non-background) market source.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import (
    create_health_router,
    create_portfolio_router,
    create_prices_router,
    create_watchlist_router,
)
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
    """Records tracked tickers without running a real background task."""

    def __init__(self) -> None:
        self.tickers: set[str] = set()

    async def start(self, tickers: list[str]) -> None:
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


@pytest.fixture
def client(cache, source) -> TestClient:
    app = FastAPI()
    app.include_router(create_health_router())
    app.include_router(create_prices_router(cache))
    app.include_router(create_portfolio_router(cache, source))
    app.include_router(create_watchlist_router(cache, source))
    return TestClient(app)
