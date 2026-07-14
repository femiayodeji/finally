"""REST API routers for FinAlly.

Public API:
    health_router          - GET /api/health liveness probe
    create_prices_router    - Router factory: GET /api/prices/{ticker}/history
    create_watchlist_router - Router factory: GET/POST/DELETE /api/watchlist
"""

from .health import router as health_router
from .prices import create_prices_router
from .watchlist import create_watchlist_router

__all__ = ["health_router", "create_prices_router", "create_watchlist_router"]
