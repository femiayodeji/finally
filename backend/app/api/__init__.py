"""REST API routers for FinAlly.

Public API:
    health_router - GET /api/health liveness probe
"""

from .health import router as health_router

__all__ = ["health_router"]
