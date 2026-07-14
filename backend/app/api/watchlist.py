"""Watchlist endpoints (PLAN §8)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.market import MarketDataSource, PriceCache
from app.services import WatchlistError, add_to_watchlist, get_watchlist, remove_from_watchlist


class AddWatchlistRequest(BaseModel):
    ticker: str


def create_watchlist_router(price_cache: PriceCache, source: MarketDataSource) -> APIRouter:
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("")
    async def list_watchlist() -> dict:
        return {"watchlist": get_watchlist(price_cache)}

    @router.post("", status_code=201)
    async def add(body: AddWatchlistRequest) -> dict:
        try:
            return await add_to_watchlist(price_cache, source, body.ticker)
        except WatchlistError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.delete("/{ticker}")
    async def remove(ticker: str) -> dict:
        ticker = ticker.upper()
        await remove_from_watchlist(price_cache, source, ticker)
        return {"ticker": ticker}

    return router
