"""Tests for GET /api/prices/{ticker}/history."""

from __future__ import annotations


def test_history_empty_for_unknown_ticker(client):
    response = client.get("/api/prices/AAPL/history")
    assert response.status_code == 200
    assert response.json() == {"ticker": "AAPL", "history": []}


def test_history_reflects_cache(client, cache):
    cache.update("AAPL", 190.0, timestamp=1000.0)
    cache.update("AAPL", 191.0, timestamp=1000.5)

    response = client.get("/api/prices/aapl/history")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["history"] == [
        {"timestamp": 1000.0, "price": 190.0},
        {"timestamp": 1000.5, "price": 191.0},
    ]
