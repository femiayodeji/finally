"""Price-history REST endpoint (PLAN.md §8, MKT-04).

`GET /api/prices/{ticker}/history` backfills sparklines and the main chart
from the in-memory `PriceCache` rolling ring buffer
(`app/market/cache.py::get_history`) — the source charts/sparklines render
from before extending live via the SSE stream (PLAN.md §10).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.market.cache import PriceCache


def create_prices_router(cache: PriceCache) -> APIRouter:
    """Router factory taking the shared PriceCache (mirrors create_stream_router)."""
    router = APIRouter(prefix="/api/prices", tags=["prices"])

    @router.get("/{ticker}/history")
    async def get_price_history(ticker: str) -> dict:
        """Recent rolling price history for a ticker.

        Returns an empty history list (200, not a 404) for an untracked
        ticker so the frontend backfill degrades gracefully rather than
        erroring (MKT-04). Path param is uppercased before the cache
        lookup — parameterized cache access only, no injection surface
        (T-04-02).
        """
        normalized = ticker.strip().upper()
        return {"ticker": normalized, "history": cache.get_history(normalized)}

    return router
