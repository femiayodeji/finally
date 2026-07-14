"""Backend service layer — the authoritative core logic (PLAN §3).

Portfolio valuation, trade execution, and watchlist management live here.
Both the REST API routers and the LLM chat layer call into these same
functions, so every code path shares one implementation of the money math
and validation rules.
"""

from .errors import TradeError, WatchlistError
from .portfolio_service import execute_trade, get_portfolio, snapshot_portfolio
from .watchlist_service import add_to_watchlist, get_watchlist, remove_from_watchlist

__all__ = [
    "TradeError",
    "WatchlistError",
    "get_portfolio",
    "snapshot_portfolio",
    "execute_trade",
    "get_watchlist",
    "add_to_watchlist",
    "remove_from_watchlist",
]
