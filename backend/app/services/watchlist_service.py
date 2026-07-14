"""Watchlist business logic: validation + DB/tracked-set orchestration.

Enforces PLAN.md §8 "Watchlist Validation" (symbol format, idempotent adds,
Massive-mode rejection of unpriceable symbols) and §6 "Tracked Ticker Set"
(watchlist ∪ open positions — a removed watchlist ticker keeps streaming
while a position is still open, MKT-05).
"""

from __future__ import annotations

import asyncio
import re

from app.db import watchlist_repo
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.market.simulator import SimulatorDataSource

# Uppercase, 1-5 ASCII letters (PLAN.md §8, T-04-01).
_SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")

# Massive mode only: MassiveDataSource.add_ticker() just registers the
# ticker for the *next* poll cycle (app/market/massive_client.py) rather
# than seeding the cache synchronously like the simulator does. Give it a
# brief window to resolve a price before deciding the symbol is unpriceable
# and rolling the add back (WATCH-03). Simulator mode — the default, tested
# path — seeds the cache synchronously in add_ticker() via default GBM
# params for unknown symbols, so this window is never exercised there.
_MASSIVE_ADD_RETRIES = 3
_MASSIVE_ADD_POLL_INTERVAL = 1.0


def validate_symbol(raw: str) -> str:
    """Normalize to uppercase and enforce the 1-5 ASCII-letter format.

    Raises ValueError with a user-facing message if the symbol is malformed
    (PLAN.md §8 Watchlist Validation; T-04-01/T-04-02 mitigation).
    """
    normalized = raw.strip().upper()
    if not _SYMBOL_RE.match(normalized):
        raise ValueError(f"Invalid ticker symbol '{raw}': must be 1-5 letters")
    return normalized


def list_watchlist(cache: PriceCache) -> list[dict]:
    """DB watchlist tickers merged with their latest cache snapshot.

    Shape matches the frontend `WatchlistEntry` contract
    (frontend/lib/types.ts): price/previous_price/change/
    session_change_percent/direction/timestamp are null until the cache has
    a tick for that ticker (WATCH-01).
    """
    entries = []
    for ticker in watchlist_repo.list_tickers():
        update = cache.get(ticker)
        if update is None:
            entries.append(
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
            entries.append(
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
    return entries


async def add(cache: PriceCache, source: MarketDataSource, ticker: str) -> str:
    """Validate, persist, and start tracking a ticker.

    Simulator mode (default, tested path): any well-formed symbol is
    accepted — `SimulatorDataSource.add_ticker()` seeds the cache
    synchronously with a deterministic default price for unknown symbols
    (PLAN.md §6). Massive mode: an unpriceable symbol is rejected and the
    add is rolled back (DB row deleted, tracking stopped) after a brief
    window for the poller to resolve it (WATCH-03).

    Raises ValueError (surfaced by the router as a 400) on an invalid or
    unpriceable symbol; nothing is persisted in that case.
    """
    normalized = validate_symbol(ticker)

    watchlist_repo.add_ticker(normalized)
    await source.add_ticker(normalized)

    if not isinstance(source, SimulatorDataSource):
        for _ in range(_MASSIVE_ADD_RETRIES):
            if cache.get(normalized) is not None:
                break
            await asyncio.sleep(_MASSIVE_ADD_POLL_INTERVAL)
        else:
            watchlist_repo.remove_ticker(normalized)
            await source.remove_ticker(normalized)
            raise ValueError(f"'{normalized}' could not be priced by the market data source")

    return normalized


async def remove(cache: PriceCache, source: MarketDataSource, ticker: str) -> str:
    """Remove a ticker from the watchlist.

    Keeps tracking (does not call `source.remove_ticker`) while an open
    position remains for the ticker (PLAN.md §6 Tracked Ticker Set, MKT-05)
    — portfolio valuation still needs a live price for held tickers even
    after they leave the watchlist.
    """
    normalized = validate_symbol(ticker)

    watchlist_repo.remove_ticker(normalized)

    if not watchlist_repo.has_open_position(normalized):
        await source.remove_ticker(normalized)

    return normalized
