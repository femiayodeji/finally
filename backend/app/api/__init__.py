"""REST API routers.

Each module exposes a `create_*_router(...)` factory that receives its
dependencies (price cache, market data source) explicitly — no module-level
singletons — mirroring `app.market.create_stream_router`.
"""

from .health import create_health_router
from .portfolio import create_portfolio_router
from .prices import create_prices_router
from .watchlist import create_watchlist_router

__all__ = [
    "create_health_router",
    "create_portfolio_router",
    "create_prices_router",
    "create_watchlist_router",
]
