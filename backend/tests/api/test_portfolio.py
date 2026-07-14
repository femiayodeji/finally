"""Tests for /api/portfolio endpoints."""

from __future__ import annotations

from app import db


def test_get_portfolio_shape(client):
    response = client.get("/api/portfolio")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "cash_balance": 10000.0,
        "positions_value": 0.0,
        "total_value": 10000.0,
        "total_unrealized_pnl": 0.0,
        "positions": [],
    }


def test_trade_buy_executes(client, cache, source):
    cache.update("AAPL", 190.0)

    response = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "buy"})
    assert response.status_code == 200
    body = response.json()
    assert body["trade"]["ticker"] == "AAPL"
    assert body["trade"]["side"] == "buy"
    assert body["portfolio"]["cash_balance"] == 10000.0 - 1900.0
    assert "AAPL" in source.tickers


def test_trade_insufficient_cash_returns_400(client, cache):
    cache.update("AAPL", 190.0)

    response = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1000, "side": "buy"}
    )
    assert response.status_code == 400
    assert "detail" in response.json()
    assert db.get_cash_balance() == 10000.0


def test_trade_sell_without_position_returns_400(client, cache):
    cache.update("AAPL", 190.0)

    response = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"}
    )
    assert response.status_code == 400


def test_portfolio_history_returns_snapshots(client, cache):
    cache.update("AAPL", 190.0)
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})

    response = client.get("/api/portfolio/history")
    assert response.status_code == 200
    history = response.json()["history"]
    assert len(history) == 1
    assert "total_value" in history[0]
    assert "recorded_at" in history[0]
