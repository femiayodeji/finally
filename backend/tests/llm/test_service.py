"""`handle_chat` orchestration tests: services + LLM client are mocked.

Verifies the flow PLAN §9 describes — context built from services, history
loaded, LLM called, actions dispatched to the right service functions with
the right args, outcomes recorded (including a failing-validation case), and
both turns persisted — without depending on the real service layer, DB
content, or a network call.
"""

from __future__ import annotations

from unittest.mock import patch

from app.db import recent_messages
from app.llm.schema import ChatResponse, Trade, WatchlistChange
from app.llm.service import handle_chat


async def _handle_chat_with_response(fake_services, response: ChatResponse, message="hi"):
    with patch("app.llm.service.complete_chat", return_value=response):
        return await handle_chat(message, cache=object(), source=object())


async def test_handle_chat_returns_message_and_empty_actions(fake_services):
    response = ChatResponse(message="Your portfolio looks balanced.")
    result = await _handle_chat_with_response(fake_services, response)

    assert result == {
        "message": "Your portfolio looks balanced.",
        "actions": {"trades": [], "watchlist_changes": []},
    }


async def test_handle_chat_builds_context_from_services(fake_services):
    response = ChatResponse(message="ok")
    await _handle_chat_with_response(fake_services, response)

    fake_services.portfolio.get_portfolio.assert_called_once()
    fake_services.watchlist.get_watchlist.assert_called_once()


async def test_handle_chat_executes_trade_with_correct_args(fake_services):
    cache, source = object(), object()
    response = ChatResponse(
        message="Buying.", trades=[Trade(ticker="AAPL", side="buy", quantity=10)]
    )

    with patch("app.llm.service.complete_chat", return_value=response):
        result = await handle_chat("buy 10 AAPL", cache, source)

    fake_services.portfolio.execute_trade.assert_awaited_once_with(
        cache, source, "AAPL", "buy", 10
    )
    assert result["actions"]["trades"] == [
        {"ticker": "AAPL", "side": "buy", "quantity": 10, "status": "executed"}
    ]


async def test_handle_chat_records_failed_trade_without_raising(fake_services):
    fake_services.portfolio.execute_trade.side_effect = fake_services.errors.TradeError(
        "Insufficient cash"
    )
    response = ChatResponse(
        message="Trying to buy.", trades=[Trade(ticker="AAPL", side="buy", quantity=1000)]
    )

    result = await _handle_chat_with_response(fake_services, response, message="buy 1000 AAPL")

    assert result["actions"]["trades"] == [
        {
            "ticker": "AAPL",
            "side": "buy",
            "quantity": 1000,
            "status": "failed",
            "error": "Insufficient cash",
        }
    ]


async def test_handle_chat_executes_watchlist_add_with_correct_args(fake_services):
    cache, source = object(), object()
    response = ChatResponse(
        message="Adding.", watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")]
    )

    with patch("app.llm.service.complete_chat", return_value=response):
        result = await handle_chat("add PYPL", cache, source)

    fake_services.watchlist.add_to_watchlist.assert_awaited_once_with(cache, source, "PYPL")
    fake_services.watchlist.remove_from_watchlist.assert_not_called()
    assert result["actions"]["watchlist_changes"] == [
        {"ticker": "PYPL", "action": "add", "status": "executed"}
    ]


async def test_handle_chat_executes_watchlist_remove_with_correct_args(fake_services):
    cache, source = object(), object()
    response = ChatResponse(
        message="Removing.", watchlist_changes=[WatchlistChange(ticker="NFLX", action="remove")]
    )

    with patch("app.llm.service.complete_chat", return_value=response):
        await handle_chat("remove NFLX", cache, source)

    fake_services.watchlist.remove_from_watchlist.assert_awaited_once_with(cache, source, "NFLX")
    fake_services.watchlist.add_to_watchlist.assert_not_called()


async def test_handle_chat_records_failed_watchlist_change(fake_services):
    fake_services.watchlist.add_to_watchlist.side_effect = fake_services.errors.WatchlistError(
        "Invalid symbol"
    )
    response = ChatResponse(
        message="Adding.", watchlist_changes=[WatchlistChange(ticker="ZZZZZZ", action="add")]
    )

    result = await _handle_chat_with_response(fake_services, response, message="add ZZZZZZ")

    assert result["actions"]["watchlist_changes"] == [
        {"ticker": "ZZZZZZ", "action": "add", "status": "failed", "error": "Invalid symbol"}
    ]


async def test_handle_chat_persists_user_and_assistant_messages(fake_services):
    response = ChatResponse(message="Here's my analysis.")
    await _handle_chat_with_response(fake_services, response, message="how am I doing?")

    messages = recent_messages(20)
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "how am I doing?"),
        ("assistant", "Here's my analysis."),
    ]
    assert messages[1]["actions"] == {"trades": [], "watchlist_changes": []}


async def test_handle_chat_loads_recent_history_for_the_llm_call(fake_services):
    from app.db import insert_message

    insert_message("user", "earlier question")
    insert_message("assistant", "earlier answer")

    response = ChatResponse(message="follow-up answer")
    with patch("app.llm.service.complete_chat", return_value=response) as mock_complete:
        await handle_chat("follow-up question", cache=object(), source=object())

    _, llm_messages = mock_complete.call_args.args
    roles_and_content = [(m["role"], m["content"]) for m in llm_messages]
    assert ("user", "earlier question") in roles_and_content
    assert ("assistant", "earlier answer") in roles_and_content
    assert roles_and_content[-1] == ("user", "follow-up question")
