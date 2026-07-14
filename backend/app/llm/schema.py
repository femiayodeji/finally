"""Structured-output schema for the LLM chat response (PLAN §9).

The model is instructed to reply with JSON matching `ChatResponse`. This is
also the shape requested from LiteLLM's structured-output support and the
shape validated against on the JSON + retry fallback path (see `client.py`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Trade(BaseModel):
    """A trade the LLM wants auto-executed, mirroring `POST /api/portfolio/trade`."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class WatchlistChange(BaseModel):
    """A watchlist mutation the LLM wants applied (mirrors PLAN §8 endpoints)."""

    ticker: str
    action: Literal["add", "remove"]


class ChatResponse(BaseModel):
    """The complete structured reply requested from the LLM."""

    message: str
    trades: list[Trade] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)
