"""Thread-safe in-memory price cache."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock

from .models import PriceUpdate

# Ring buffer length for rolling price history: ~600 points at 500ms ticks
# is a few minutes of history, enough to backfill charts/sparklines on load.
HISTORY_MAXLEN = 600


class PriceCache:
    """Thread-safe in-memory cache of the latest price for each ticker.

    Writers: SimulatorDataSource or MassiveDataSource (one at a time).
    Readers: SSE streaming endpoint, portfolio valuation, trade execution.
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0  # Monotonically increasing; bumped on every update
        self._session_reference: dict[str, float] = {}  # First observed price per ticker
        self._history: dict[str, deque[tuple[float, float]]] = {}  # ticker -> (timestamp, price)

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Record a new price for a ticker. Returns the created PriceUpdate.

        Automatically computes direction and change from the previous price.
        If this is the first update for the ticker, previous_price == price (direction='flat').
        The session reference (open) price is captured on the first observation
        and carried on every subsequent update for that ticker.
        """
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price
            rounded_price = round(price, 2)

            session_reference = self._session_reference.get(ticker)
            if session_reference is None:
                session_reference = rounded_price
                self._session_reference[ticker] = session_reference

            update = PriceUpdate(
                ticker=ticker,
                price=rounded_price,
                previous_price=round(previous_price, 2),
                timestamp=ts,
                session_reference=session_reference,
            )
            self._prices[ticker] = update
            self._history.setdefault(ticker, deque(maxlen=HISTORY_MAXLEN)).append((ts, rounded_price))
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        """Get the latest price for a single ticker, or None if unknown."""
        with self._lock:
            return self._prices.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        """Snapshot of all current prices. Returns a shallow copy."""
        with self._lock:
            return dict(self._prices)

    def get_price(self, ticker: str) -> float | None:
        """Convenience: get just the price float, or None."""
        update = self.get(ticker)
        return update.price if update else None

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache (e.g., when removed from watchlist)."""
        with self._lock:
            self._prices.pop(ticker, None)
            self._session_reference.pop(ticker, None)
            self._history.pop(ticker, None)

    def get_history(self, ticker: str) -> list[dict]:
        """Return the rolling price history for a ticker, oldest first.

        Each entry is `{"timestamp": ..., "price": ...}`. Empty list if the
        ticker has no recorded history (unknown, or removed).
        """
        with self._lock:
            history = self._history.get(ticker)
            if not history:
                return []
            return [{"timestamp": ts, "price": price} for ts, price in history]

    @property
    def version(self) -> int:
        """Current version counter. Useful for SSE change detection."""
        return self._version

    def __len__(self) -> int:
        with self._lock:
            return len(self._prices)

    def __contains__(self, ticker: str) -> bool:
        with self._lock:
            return ticker in self._prices
