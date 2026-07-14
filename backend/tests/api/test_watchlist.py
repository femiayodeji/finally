"""Tests for /api/watchlist endpoints."""

from __future__ import annotations

from app import db


def test_get_watchlist_returns_seeded_tickers(client):
    response = client.get("/api/watchlist")
    assert response.status_code == 200
    tickers = {entry["ticker"] for entry in response.json()["watchlist"]}
    assert "AAPL" in tickers
    assert len(tickers) == 10


def test_post_watchlist_adds_ticker(client, source):
    response = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert response.status_code == 201
    assert response.json() == {"ticker": "PYPL"}
    assert db.is_watchlisted("PYPL")
    assert "PYPL" in source.tickers


def test_post_watchlist_rejects_invalid_symbol(client):
    response = client.post("/api/watchlist", json={"ticker": "TOOLONG"})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_delete_watchlist_removes_ticker(client, source):
    client.post("/api/watchlist", json={"ticker": "PYPL"})

    response = client.delete("/api/watchlist/PYPL")
    assert response.status_code == 200
    assert response.json() == {"ticker": "PYPL"}
    assert not db.is_watchlisted("PYPL")
    assert "PYPL" not in source.tickers


def test_delete_watchlist_keeps_tracking_open_position(client, source):
    client.post("/api/watchlist", json={"ticker": "PYPL"})
    db.upsert_position("PYPL", 3, 10.0)

    response = client.delete("/api/watchlist/PYPL")
    assert response.status_code == 200
    assert not db.is_watchlisted("PYPL")
    assert "PYPL" in source.tickers
