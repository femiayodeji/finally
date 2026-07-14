"""FastAPI composition root (PLAN.md §3, §11).

Wires the ASGI lifespan in strict order: DB init/seed -> PriceCache ->
tracked-ticker union (watchlist ∪ open positions) -> market data source
start -> routers -> static frontend serving (mounted last so it never
shadows /api/*).

`create_app()` is a factory (no module-level singletons, per
`.planning/codebase/ARCHITECTURE.md` "Global state" constraint) so the same
`PriceCache` instance is threaded through the lifespan, the market data
source, and `create_stream_router` — and so tests can build isolated app
instances.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.api import create_prices_router, create_watchlist_router, health_router
from app.market import create_market_data_source, create_stream_router
from app.market.cache import PriceCache

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_DEFAULT_STATIC_DIR = _PROJECT_ROOT / "frontend" / "out"


def get_static_dir() -> Path:
    """Resolve the Next.js static export directory, env-overridable for tests."""
    override = os.environ.get("FINALLY_STATIC_DIR", "").strip()
    return Path(override) if override else _DEFAULT_STATIC_DIR


def _mount_static(app: FastAPI) -> None:
    """Serve the Next.js static export for all non-/api routes (APP-02).

    Mounted at "/" AFTER all API routers so it cannot intercept /api/*
    (T-01-01). A missing export directory (common during backend-only dev,
    before `npm run build` has produced frontend/out) logs a warning
    instead of crashing the app (T-01-02).
    """
    static_dir = get_static_dir()
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    else:
        logger.warning(
            "Static export directory not found at %s — frontend will not be served "
            "until `npm run build` produces it",
            static_dir,
        )


def create_app() -> FastAPI:
    """Build and return the FastAPI application.

    The PriceCache is created here, once, and closed over by the lifespan
    below — the same instance is passed to the market data source and to
    `create_stream_router` (single seam for future multi-user scaling,
    PLAN.md §3).
    """
    cache = PriceCache()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """App startup/shutdown. Order matters (APP-01/02/03):

        1. db.initialize() — schema + seed must exist before any market work
        2. tracked = watchlist ∪ open positions (PLAN.md §6 Tracked Ticker Set)
        3. create_market_data_source(cache).start(tracked)
        """
        db.initialize()

        tracked = db.get_tracked_tickers()

        source = create_market_data_source(cache)
        await source.start(tracked)

        app.state.cache = cache
        app.state.market_source = source

        logger.info("FinAlly backend started; tracking %d ticker(s)", len(tracked))

        yield

        await source.stop()
        logger.info("FinAlly backend shut down")

    app = FastAPI(title="FinAlly", lifespan=lifespan)

    # --- Router registration site ---------------------------------------
    # Registered before the static mount below (StaticFiles must be mounted
    # last so it never shadows /api/* — T-01-01). Add new routers to this
    # block as later plans build them:
    #   - GET /api/prices/{ticker}/history          (Plan 04) ✅
    #   - GET/POST/DELETE /api/watchlist             (Plan 04) ✅
    #   - GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history (Plan 03)
    #   - POST /api/chat                             (Plan 05/06)
    #
    # create_prices_router/create_watchlist_router close over `cache` only
    # (available here, before the lifespan runs). The watchlist router's
    # mutating routes read `request.app.state.market_source` at request
    # time instead, since the market source isn't constructed until inside
    # the lifespan above (APP-03 order: db.initialize() -> tracked tickers
    # -> source.start()) — see app/api/watchlist.py module docstring.
    app.include_router(health_router)
    app.include_router(create_stream_router(cache))
    app.include_router(create_prices_router(cache))
    app.include_router(create_watchlist_router(cache))

    _mount_static(app)

    return app


app = create_app()
