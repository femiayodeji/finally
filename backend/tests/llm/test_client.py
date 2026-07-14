"""LLM client tests: mock-mode determinism + structured-output retry/fallback.

No real network calls are made — `LLM_MOCK` short-circuits the network, and
`litellm.completion` is monkeypatched for the non-mock path.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

import app.config
from app.llm import client
from app.llm.schema import ChatResponse, Trade, WatchlistChange


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    """Default every test to mock mode; individual tests opt out explicitly.

    `app.config.LLM_MOCK` is a module-level constant read once at import
    time, so it's patched directly rather than via the `LLM_MOCK` env var
    (which only affects a *fresh* import of `app.config`).
    """
    monkeypatch.setattr(app.config, "LLM_MOCK", True)


# --- mock mode ----------------------------------------------------------------


def test_mock_mode_generic_message_has_no_actions():
    response = client.complete_chat("system", [{"role": "user", "content": "how am I doing?"}])
    assert response.trades == []
    assert response.watchlist_changes == []
    assert "FinAlly" in response.message


def test_mock_mode_parses_buy_intent():
    response = client.complete_chat("system", [{"role": "user", "content": "buy 10 AAPL"}])
    assert response.trades == [Trade(ticker="AAPL", side="buy", quantity=10.0)]


def test_mock_mode_parses_sell_intent_with_shares_of_phrasing():
    response = client.complete_chat(
        "system", [{"role": "user", "content": "please sell 2.5 shares of TSLA"}]
    )
    assert response.trades[0].ticker == "TSLA"
    assert response.trades[0].side == "sell"
    assert response.trades[0].quantity == 2.5


def test_mock_mode_parses_watchlist_add():
    response = client.complete_chat("system", [{"role": "user", "content": "add PYPL to my watchlist"}])
    assert response.watchlist_changes == [WatchlistChange(ticker="PYPL", action="add")]
    assert response.trades == []


def test_mock_mode_parses_watchlist_remove():
    response = client.complete_chat(
        "system", [{"role": "user", "content": "remove NFLX from my watchlist"}]
    )
    assert response.watchlist_changes == [WatchlistChange(ticker="NFLX", action="remove")]


def test_mock_mode_is_deterministic():
    messages = [{"role": "user", "content": "buy 5 MSFT"}]
    first = client.complete_chat("system", messages)
    second = client.complete_chat("system", messages)
    assert first == second


def test_mock_mode_uses_last_user_message():
    messages = [
        {"role": "user", "content": "buy 5 AAPL"},
        {"role": "assistant", "content": "Executed."},
        {"role": "user", "content": "add PYPL to my watchlist"},
    ]
    response = client.complete_chat("system", messages)
    assert response.trades == []
    assert response.watchlist_changes == [WatchlistChange(ticker="PYPL", action="add")]


# --- real call path (litellm mocked) ------------------------------------------


def _install_fake_litellm(monkeypatch, completion_fn):
    fake_litellm = types.ModuleType("litellm")
    fake_litellm.completion = completion_fn
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)


def _fake_response(content: str):
    message = MagicMock(content=content)
    choice = MagicMock(message=message)
    return MagicMock(choices=[choice])


def test_call_llm_returns_validated_response_on_first_try(monkeypatch):
    monkeypatch.setattr(app.config, "LLM_MOCK", False)
    valid_json = '{"message": "Looks balanced.", "trades": [], "watchlist_changes": []}'
    completion_fn = MagicMock(return_value=_fake_response(valid_json))
    _install_fake_litellm(monkeypatch, completion_fn)

    response = client.complete_chat("system", [{"role": "user", "content": "how am I doing?"}])

    assert response == ChatResponse(message="Looks balanced.")
    completion_fn.assert_called_once()


def test_call_llm_retries_once_on_malformed_output_then_succeeds(monkeypatch):
    monkeypatch.setattr(app.config, "LLM_MOCK", False)
    valid_json = '{"message": "ok", "trades": [], "watchlist_changes": []}'
    completion_fn = MagicMock(
        side_effect=[_fake_response("not valid json"), _fake_response(valid_json)]
    )
    _install_fake_litellm(monkeypatch, completion_fn)

    response = client.complete_chat("system", [{"role": "user", "content": "hi"}])

    assert response.message == "ok"
    assert completion_fn.call_count == 2


def test_call_llm_falls_back_gracefully_after_repeated_malformed_output(monkeypatch):
    monkeypatch.setattr(app.config, "LLM_MOCK", False)
    completion_fn = MagicMock(return_value=_fake_response("still not valid json"))
    _install_fake_litellm(monkeypatch, completion_fn)

    response = client.complete_chat("system", [{"role": "user", "content": "hi"}])

    assert response.trades == []
    assert response.watchlist_changes == []
    assert completion_fn.call_count == 2  # initial attempt + one retry, no more
