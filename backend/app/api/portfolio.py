"""Portfolio endpoints (PLAN §8): valuation, trade execution, value history."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.market import MarketDataSource, PriceCache
from app.services import TradeError, execute_trade, get_portfolio


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str


def create_portfolio_router(price_cache: PriceCache, source: MarketDataSource) -> APIRouter:
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("")
    async def portfolio() -> dict:
        return get_portfolio(price_cache)

    @router.post("/trade")
    async def trade(body: TradeRequest) -> dict:
        try:
            return await execute_trade(
                price_cache, source, body.ticker, body.side, body.quantity
            )
        except TradeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/history")
    async def history() -> dict:
        return {"history": db.list_snapshots()}

    return router
