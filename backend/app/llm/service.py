"""Chat orchestration: context + history -> LLM -> auto-execute -> persist (PLAN §9).

Service functions (`app.services.*`) are imported lazily inside the helpers
below rather than at module import time. `app/services/` is owned by the
Backend API Engineer and built in parallel — importing it eagerly here would
make this module (and everything that imports it) fail to load while that
work is in progress. Unit tests stub the service modules via `sys.modules`
so this module's own logic is testable independent of that work landing.
"""

from __future__ import annotations

import asyncio
import json
import logging

from app.market import MarketDataSource, PriceCache

from .client import complete_chat
from .schema import ChatResponse, Trade, WatchlistChange

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are FinAlly, an AI trading assistant for a simulated trading platform. "
    "Analyze the user's portfolio composition, risk concentration, and P&L. "
    "Suggest trades with clear reasoning. Execute a trade when the user asks for "
    "one or agrees to a suggestion you made. Manage the watchlist proactively "
    "when it helps the user. Be concise and data-driven. Trades and watchlist "
    "changes you include in your response execute automatically — there is no "
    "confirmation step, so only include actions you actually intend to happen. "
    "Always respond with valid JSON matching the required schema: "
    '{"message": str, "trades": [{"ticker": str, "side": "buy"|"sell", '
    '"quantity": number}], "watchlist_changes": [{"ticker": str, "action": '
    '"add"|"remove"}]}.'
)


def _build_context(cache: PriceCache) -> str:
    """Portfolio + watchlist snapshot for the system prompt (PLAN §9 step 1)."""
    from app.services.portfolio_service import get_portfolio
    from app.services.watchlist_service import get_watchlist

    portfolio = get_portfolio(cache)
    watchlist = get_watchlist(cache)
    return (
        "Current portfolio (JSON):\n"
        f"{json.dumps(portfolio, default=str)}\n\n"
        "Current watchlist (JSON):\n"
        f"{json.dumps(watchlist, default=str)}"
    )


def _history_to_messages(history: list[dict]) -> list[dict]:
    return [{"role": h["role"], "content": h["content"]} for h in history]


async def _execute_trades(cache: PriceCache, source: MarketDataSource, trades: list[Trade]) -> list[dict]:
    from app.services.errors import TradeError
    from app.services.portfolio_service import execute_trade

    results = []
    for trade in trades:
        entry = {"ticker": trade.ticker, "side": trade.side, "quantity": trade.quantity}
        try:
            await execute_trade(cache, source, trade.ticker, trade.side, trade.quantity)
            entry["status"] = "executed"
        except TradeError as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
        results.append(entry)
    return results


async def _execute_watchlist_changes(
    cache: PriceCache, source: MarketDataSource, changes: list[WatchlistChange]
) -> list[dict]:
    from app.services.errors import WatchlistError
    from app.services.watchlist_service import add_to_watchlist, remove_from_watchlist

    results = []
    for change in changes:
        entry = {"ticker": change.ticker, "action": change.action}
        try:
            if change.action == "add":
                await add_to_watchlist(cache, source, change.ticker)
            else:
                await remove_from_watchlist(cache, source, change.ticker)
            entry["status"] = "executed"
        except WatchlistError as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
        results.append(entry)
    return results


async def handle_chat(message: str, cache: PriceCache, source: MarketDataSource) -> dict:
    """Handle one chat turn end to end (PLAN §9 steps 1-7).

    Builds portfolio/watchlist context, loads the last 20 messages, calls the
    LLM for a validated `ChatResponse`, auto-executes any trades/watchlist
    changes it specifies (never acting on an unvalidated payload), persists
    both turns, and returns `{"message": ..., "actions": {...}}`.
    """
    from app.db import insert_message, recent_messages

    system = f"{SYSTEM_PROMPT}\n\n{_build_context(cache)}"
    history = _history_to_messages(recent_messages(20))
    llm_messages = [*history, {"role": "user", "content": message}]

    response: ChatResponse = await asyncio.to_thread(complete_chat, system, llm_messages)

    trade_results = await _execute_trades(cache, source, response.trades)
    watchlist_results = await _execute_watchlist_changes(cache, source, response.watchlist_changes)

    actions = {"trades": trade_results, "watchlist_changes": watchlist_results}

    insert_message("user", message)
    insert_message("assistant", response.message, actions=actions)

    return {"message": response.message, "actions": actions}
