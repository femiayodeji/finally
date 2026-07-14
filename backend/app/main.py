"""FastAPI application entrypoint — app wiring, lifespan, router mounting (PLAN §2)."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.api import (
    create_health_router,
    create_portfolio_router,
    create_prices_router,
    create_watchlist_router,
)
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.services import snapshot_portfolio

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL_SECONDS = 30

# Static frontend export (Next.js `output: 'export'`), copied into the image
# by the Dockerfile at build time. Absent in local dev — mounted only if present.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def _snapshot_loop(cache: PriceCache) -> None:
    """Background task: record a portfolio_snapshots row every 30s (PLAN §7)."""
    while True:
        await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(snapshot_portfolio, cache)
        except Exception:
            logger.exception("Portfolio snapshot loop failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Schema + seed data before anything reads the DB.
    db.init_db()

    # 2. Cache + market data source, started against the tracked set
    #    (watchlist ∪ open positions — PLAN §6) so the price task never
    #    has to wait for a first request to know what to stream.
    price_cache = PriceCache()
    market_source = create_market_data_source(price_cache)
    tracked = set(db.list_watchlist()) | {p["ticker"] for p in db.list_positions()}
    await market_source.start(sorted(tracked))

    app.state.price_cache = price_cache
    app.state.market_source = market_source

    # 3. Routers are created here, not at import time, because they close
    #    over the cache/source instances constructed above.
    app.include_router(create_stream_router(price_cache))
    app.include_router(create_prices_router(price_cache))
    app.include_router(create_portfolio_router(price_cache, market_source))
    app.include_router(create_watchlist_router(price_cache, market_source))

    try:
        from app.llm import create_chat_router

        app.include_router(create_chat_router(price_cache, market_source))
    except ImportError:
        logger.warning("app.llm not available yet — chat endpoint not mounted")

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    # 4. 30s portfolio_snapshots cadence (PLAN §7), in addition to the
    #    post-trade snapshot taken inline by execute_trade.
    snapshot_task = asyncio.create_task(_snapshot_loop(price_cache), name="snapshot-loop")

    try:
        yield
    finally:
        snapshot_task.cancel()
        try:
            await snapshot_task
        except asyncio.CancelledError:
            pass
        await market_source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)
app.include_router(create_health_router())
