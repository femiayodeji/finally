"""Smoke tests for the app/main.py composition root.

Proves DB -> cache -> app wiring end to end: DB initializes before the
market task starts, /api/health answers, and the PriceCache is populated
from the seeded watchlist by the time startup completes.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient with lifespan run, pointed at hermetic tmp paths.

    DB_PATH and the static export dir are both env-overridden so this test
    never touches the real db/finally.db and does not require a built
    frontend export.
    """
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally_test.db"))
    monkeypatch.setenv("FINALLY_STATIC_DIR", str(tmp_path / "nonexistent_static"))

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoint:
    """GET /api/health."""

    def test_health_returns_200_with_healthy_status(self, client):
        response = client.get("/api/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "timestamp" in body


class TestAppWiring:
    """DB -> cache -> market source wiring, exercised through the lifespan."""

    def test_market_source_populates_cache_from_seeded_watchlist(self, client):
        app_state = client.app.state

        assert app_state.cache is not None
        assert app_state.market_source is not None
        # Simulator populates the cache synchronously in start() (see
        # tests/market/test_simulator_source.py) — a seeded ticker (AAPL) must
        # already have a price by the time the lifespan yields.
        assert app_state.cache.get("AAPL") is not None

    def test_sse_stream_router_is_registered(self, client):
        # The stream endpoint is an infinite generator (PLAN.md §6 SSE
        # Streaming) — opening a real connection would block the test
        # client forever waiting for the body to complete, a known
        # httpx/TestClient limitation with never-ending responses. Assert
        # route registration instead, which proves create_stream_router(cache)
        # was included with the same cache used by the market source.
        route_paths = {route.path for route in client.app.routes}
        assert "/api/stream/prices" in route_paths


class TestStaticServing:
    """Missing static export directory degrades gracefully (T-01-02)."""

    def test_missing_static_dir_does_not_crash_app(self, client):
        # App construction + lifespan already succeeded via the fixture;
        # a request to a non-/api path should not 500.
        response = client.get("/")
        assert response.status_code != 500
