"""Watchlist management (PLAN §6, §8).

Implements the tracked-set rule: the market-data source tracks the union of
the watchlist and every ticker with an open position. Adding to the
watchlist always starts tracking; removing from the watchlist stops
tracking only if no open position remains for that ticker.
"""

from __future__ import annotations

import re

from app import db
from app.market import MarketDataSource, PriceCache

from .errors import WatchlistError

_SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")


def get_watchlist(cache: PriceCache) -> list[dict]:
    """Watchlist tickers with their latest cached price snapshot.

    Price fields are null until the ticker's first tick lands in the cache
    (e.g., immediately after being added). SSE is the source of truth for
    live updates thereafter — this is an initial-paint snapshot (PLAN §10).
    """
    out = []
    for ticker in db.list_watchlist():
        update = cache.get(ticker)
        if update is None:
            out.append(
                {
                    "ticker": ticker,
                    "price": None,
                    "previous_price": None,
                    "change": None,
                    "session_change_percent": None,
                    "direction": None,
                    "timestamp": None,
                }
            )
        else:
            out.append(
                {
                    "ticker": ticker,
                    "price": update.price,
                    "previous_price": update.previous_price,
                    "change": update.change,
                    "session_change_percent": update.session_change_percent,
                    "direction": update.direction,
                    "timestamp": update.timestamp,
                }
            )
    return out


async def add_to_watchlist(cache: PriceCache, source: MarketDataSource, ticker: str) -> dict:
    """Validate and add a ticker to the watchlist. Idempotent.

    Symbol format: 1-5 letters, normalized to uppercase (PLAN §8). Simulator
    mode accepts any well-formed symbol; unknown tickers get a deterministic
    default seed price on their first tick (handled by the simulator itself).
    """
    ticker = ticker.strip().upper()
    if not _SYMBOL_RE.match(ticker):
        raise WatchlistError(f"Invalid ticker symbol '{ticker}': must be 1-5 letters")

    db.add_watchlist(ticker)
    await source.add_ticker(ticker)
    return {"ticker": ticker}


async def remove_from_watchlist(cache: PriceCache, source: MarketDataSource, ticker: str) -> None:
    """Remove a ticker from the watchlist.

    Price tracking continues if the user still holds an open position in it
    (PLAN §6 tracked ticker set) — only stop tracking when both the
    watchlist entry and the position are gone.
    """
    ticker = ticker.strip().upper()
    db.remove_watchlist(ticker)
    if db.get_position(ticker) is None:
        await source.remove_ticker(ticker)
