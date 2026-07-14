"""Tests for GET /api/prices/{ticker}/history (PLAN.md §8, MKT-04)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient with lifespan run, pointed at hermetic tmp paths."""
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally_test.db"))
    monkeypatch.setenv("FINALLY_STATIC_DIR", str(tmp_path / "nonexistent_static"))

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestPriceHistoryRoute:
    """GET /api/prices/{ticker}/history."""

    def test_known_ticker_returns_populated_history(self, client):
        # AAPL is in the default seeded watchlist; the simulator seeds the
        # cache (and therefore history) synchronously on startup.
        response = client.get("/api/prices/AAPL/history")

        assert response.status_code == 200
        body = response.json()
        assert body["ticker"] == "AAPL"
        assert len(body["history"]) >= 1
        assert set(body["history"][0].keys()) == {"timestamp", "price"}

    def test_unknown_ticker_returns_empty_history_not_404(self, client):
        response = client.get("/api/prices/ZZZZ/history")

        assert response.status_code == 200
        assert response.json() == {"ticker": "ZZZZ", "history": []}

    def test_lowercase_ticker_is_uppercased(self, client):
        response = client.get("/api/prices/aapl/history")

        assert response.status_code == 200
        assert response.json()["ticker"] == "AAPL"
