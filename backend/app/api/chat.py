"""POST /api/chat — chat with the AI trading assistant (PLAN §8/§9)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.llm.service import handle_chat
from app.market import MarketDataSource, PriceCache


class ChatRequest(BaseModel):
    message: str


def create_chat_router(cache: PriceCache, source: MarketDataSource) -> APIRouter:
    """Create the chat router with references to the shared cache and data source.

    Factory pattern (matches `create_stream_router`) — no module-global state.
    """
    router = APIRouter(tags=["chat"])

    @router.post("/api/chat")
    async def chat(request: ChatRequest) -> dict:
        return await handle_chat(request.message, cache, source)

    return router
