"""Structured-output schema validation (PLAN §9)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.llm.schema import ChatResponse, Trade, WatchlistChange


def test_chat_response_minimal():
    response = ChatResponse(message="hello")
    assert response.message == "hello"
    assert response.trades == []
    assert response.watchlist_changes == []


def test_chat_response_full():
    response = ChatResponse(
        message="Buying AAPL",
        trades=[{"ticker": "AAPL", "side": "buy", "quantity": 10}],
        watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
    )
    assert response.trades == [Trade(ticker="AAPL", side="buy", quantity=10)]
    assert response.watchlist_changes == [WatchlistChange(ticker="PYPL", action="add")]


def test_chat_response_from_json_round_trip():
    payload = (
        '{"message": "ok", "trades": [{"ticker": "TSLA", "side": "sell", "quantity": 2.5}], '
        '"watchlist_changes": []}'
    )
    response = ChatResponse.model_validate_json(payload)
    assert response.trades[0].ticker == "TSLA"
    assert response.trades[0].side == "sell"
    assert response.trades[0].quantity == 2.5


def test_trade_rejects_invalid_side():
    with pytest.raises(ValidationError):
        Trade(ticker="AAPL", side="hold", quantity=1)


def test_watchlist_change_rejects_invalid_action():
    with pytest.raises(ValidationError):
        WatchlistChange(ticker="AAPL", action="modify")


def test_chat_response_requires_message():
    with pytest.raises(ValidationError):
        ChatResponse()


def test_chat_response_rejects_malformed_json():
    with pytest.raises(ValidationError):
        ChatResponse.model_validate_json("{not valid json")
