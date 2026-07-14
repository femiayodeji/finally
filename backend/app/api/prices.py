"""Price history endpoint — backfills charts/sparklines on load (PLAN §6, §8)."""

from __future__ import annotations

from fastapi import APIRouter

from app.market import PriceCache


def create_prices_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter(prefix="/api/prices", tags=["prices"])

    @router.get("/{ticker}/history")
    async def get_price_history(ticker: str) -> dict:
        ticker = ticker.upper()
        return {"ticker": ticker, "history": price_cache.get_history(ticker)}

    return router
