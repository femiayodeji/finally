"""Watchlist REST endpoints (PLAN.md §8 Watchlist; WATCH-01..04).

Router factory closes over the shared `PriceCache` (created before the
lifespan runs, same pattern as `create_stream_router`/`create_prices_router`).
The market data source, however, is only constructed *inside* the lifespan
(it needs `db.get_tracked_tickers()`, which needs `db.initialize()` to have
already run — APP-03 startup order) — so it isn't available yet at router
*registration* time. Mutating endpoints instead read `request.app.state.
market_source` at *request* time, by which point the lifespan has completed
and the source is guaranteed to be set.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.market.cache import PriceCache
from app.services import watchlist_service


class WatchlistAddRequest(BaseModel):
    """POST /api/watchlist body: `{"ticker": "PYPL"}`."""

    ticker: str


def create_watchlist_router(cache: PriceCache) -> APIRouter:
    """Router factory taking the shared PriceCache."""
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("")
    async def get_watchlist() -> dict:
        """WATCH-01: current watchlist tickers with a latest-price snapshot."""
        return {"watchlist": watchlist_service.list_watchlist(cache)}

    @router.post("")
    async def add_to_watchlist(body: WatchlistAddRequest, request: Request) -> dict:
        """WATCH-02/03: add a validated ticker; idempotent on duplicates."""
        source = request.app.state.market_source
        try:
            ticker = await watchlist_service.add(cache, source, body.ticker)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ticker": ticker}

    @router.delete("/{ticker}")
    async def remove_from_watchlist(ticker: str, request: Request) -> dict:
        """WATCH-04: remove from the watchlist; keep tracking an open position."""
        source = request.app.state.market_source
        try:
            normalized = await watchlist_service.remove(cache, source, ticker)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ticker": normalized}

    return router
