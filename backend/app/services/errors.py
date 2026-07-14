"""Service-layer exceptions.

Raised by `portfolio_service` / `watchlist_service` on validation failure.
API routers catch these and translate them to HTTP 400 `{"detail": message}`;
the LLM chat layer catches them to report a failed action back to the model.
"""

from __future__ import annotations


class TradeError(Exception):
    """A trade could not be executed (insufficient cash/shares, bad input)."""


class WatchlistError(Exception):
    """A watchlist change could not be applied (bad symbol, unresolvable ticker)."""
