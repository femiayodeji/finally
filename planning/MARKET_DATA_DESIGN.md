# Market Data Backend — Detailed Design

Implementation-ready design for the FinAlly market data subsystem: the unified
`MarketDataSource` interface, the GBM simulator, the Massive (Polygon.io) REST
client, the shared price cache, the SSE streaming endpoint, and the REST
history endpoint. Everything lives under `backend/app/market/`.

**Status of this document.** The core subsystem (unified interface, simulator,
Massive client, SSE stream) is already built and tested —
see `planning/MARKET_DATA_SUMMARY.md` and `planning/archive/`. This document
supersedes `planning/archive/MARKET_DATA_DESIGN.md`: it reproduces the parts
that are unchanged and adds the three extensions §3 of `PLAN.md` calls out as
still required for the **backend-owns-the-core** principle — a per-ticker
**session reference (open) price**, a bounded **rolling price history** ring
buffer, and **server-computed change %** — plus the REST endpoint that exposes
history to the frontend. §13 marks each code block `[existing]` or `[new]`.

---

## Table of Contents

1. [Architecture](#1-architecture)
2. [File Structure](#2-file-structure)
3. [Data Model — `models.py`](#3-data-model)
4. [Price Cache — `cache.py`](#4-price-cache)
5. [Abstract Interface — `interface.py`](#5-abstract-interface)
6. [Seed Prices & Ticker Parameters — `seed_prices.py`](#6-seed-prices--ticker-parameters)
7. [GBM Simulator — `simulator.py`](#7-gbm-simulator)
8. [Massive API Client — `massive_client.py`](#8-massive-api-client)
9. [Factory — `factory.py`](#9-factory)
10. [SSE Streaming Endpoint — `stream.py`](#10-sse-streaming-endpoint)
11. [Price History REST Endpoint](#11-price-history-rest-endpoint)
12. [Tracked Ticker Set — Watchlist ∪ Positions](#12-tracked-ticker-set--watchlist--positions)
13. [FastAPI Lifecycle Integration](#13-fastapi-lifecycle-integration)
14. [Testing Strategy](#14-testing-strategy)
15. [Error Handling & Edge Cases](#15-error-handling--edge-cases)
16. [Configuration Summary](#16-configuration-summary)
17. [Implementation Checklist](#17-implementation-checklist)

---

## 1. Architecture

```
MarketDataSource (ABC)
├── SimulatorDataSource  →  GBM simulator (default, no API key needed)
└── MassiveDataSource    →  Polygon.io REST poller (when MASSIVE_API_KEY set)
        │
        ▼
   PriceCache (thread-safe, in-memory)
     ├── latest PriceUpdate per ticker   (price, previous_price, direction — tick flash)
     ├── session_open per ticker         (first observed price this process run)
     ├── rolling history ring buffer     (~600 points per ticker, for charts)
     └── version counter                 (change detection for SSE)
        │
        ├──→ GET /api/stream/prices          (SSE, ~500ms, all tracked tickers)
        ├──→ GET /api/prices/{ticker}/history (REST, backfill charts/sparklines)
        ├──→ Portfolio valuation
        └──→ Trade execution
```

Two data sources implement one interface (`MarketDataSource`); everything
downstream — SSE, REST, portfolio, trades — reads from `PriceCache` and never
touches the data source directly or knows which implementation is active.

**Two kinds of "change" travel through this system, and they must not be
conflated:**

| Field | Baseline | Purpose |
|---|---|---|
| `change`, `direction` | previous tick's price | Drives the CSS flash animation (green/red) on each SSE tick |
| `change_percent` | **session-open price** (first price observed this process run) | The stable "% change" shown next to a ticker; identical across every client and every reload, because its reference lives server-side |

A naive implementation that computes `change_percent` from `previous_price`
would make every client's displayed % change depend on when it happened to
connect — violating §3 and §10 of `PLAN.md` ("Change % is stable across
reloads"). The cache therefore tracks `session_open` independently of
`previous_price`.

---

## 2. File Structure

```
backend/
  app/
    market/
      __init__.py             # Re-exports the public API
      models.py                # PriceUpdate dataclass                              [modified]
      cache.py                 # PriceCache: latest price, session open, history     [modified]
      interface.py              # MarketDataSource ABC                                [existing]
      seed_prices.py            # SEED_PRICES, TICKER_PARAMS, correlation groups      [existing]
      simulator.py               # GBMSimulator + SimulatorDataSource                  [existing]
      massive_client.py          # MassiveDataSource                                   [existing]
      factory.py                  # create_market_data_source()                        [existing]
      stream.py                    # SSE endpoint + price history REST endpoint         [modified]
```

No new files are needed — the extensions are additive changes to `models.py`,
`cache.py`, and `stream.py`. `interface.py`, `seed_prices.py`, `simulator.py`,
`massive_client.py`, and `factory.py` are unchanged; they are reproduced below
for a complete, self-contained reference.

---

## 3. Data Model

**File: `backend/app/market/models.py`** — `[modified]`

`PriceUpdate` is the only data structure that leaves the market data layer.
It now carries both the tick-level baseline (`previous_price`) and the
session-level baseline (`session_open`), each backing a different derived
property.

```python
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Immutable snapshot of a single ticker's price at a point in time."""

    ticker: str
    price: float
    previous_price: float          # prior tick's price — for flash direction
    session_open: float            # first observed price this process run
    timestamp: float = field(default_factory=time.time)  # Unix seconds

    @property
    def change(self) -> float:
        """Absolute tick-over-tick price change. Drives the flash amount, if used."""
        return round(self.price - self.previous_price, 4)

    @property
    def direction(self) -> str:
        """'up', 'down', or 'flat' — tick-over-tick, for the CSS flash color."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"

    @property
    def change_percent(self) -> float:
        """Percentage change from the session-open reference price.

        This is the "change %" shown in the watchlist/positions table. It is
        computed against `session_open`, not `previous_price`, so every
        connected client sees the identical value regardless of when it
        connected — the reference lives server-side, in the cache.
        """
        if self.session_open == 0:
            return 0.0
        return round((self.price - self.session_open) / self.session_open * 100, 4)

    def to_dict(self) -> dict:
        """Serialize for JSON / SSE transmission."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "session_open": self.session_open,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
        }
```

### Design decisions

- **`frozen=True, slots=True`** — unchanged rationale: immutable value objects, safe to share across async tasks, memory-efficient at high creation rates.
- **Two baselines, two properties.** `previous_price` → `change`/`direction` (tick flash). `session_open` → `change_percent` (stable display value). Neither can be derived from the other.
- **`to_dict()`** remains the single serialization point used by both the SSE endpoint and the history REST endpoint.

---

## 4. Price Cache

**File: `backend/app/market/cache.py`** — `[modified]`

The price cache is the central data hub — data sources write to it, SSE
streaming and the history endpoint read from it. It is thread-safe because
the Massive poller's synchronous call runs via `asyncio.to_thread`, a real OS
thread, which an `asyncio.Lock` would not protect against.

```python
from __future__ import annotations

import time
from collections import deque
from threading import Lock

from .models import PriceUpdate

# ~600 points ≈ 5 minutes of history at the 500ms SSE/simulator cadence.
# Bounded so memory is O(tickers × HISTORY_MAXLEN), not unbounded over a
# long-running process. In-memory only — not persisted to SQLite (per-tick
# writes would hurt latency); the durable time series is `portfolio_snapshots`.
HISTORY_MAXLEN = 600


class PriceCache:
    """Thread-safe in-memory cache of price state for each ticker.

    Writers: SimulatorDataSource or MassiveDataSource (one at a time).
    Readers: SSE streaming endpoint, the price-history REST endpoint,
    portfolio valuation, trade execution.

    Per ticker, the cache holds:
      - the latest PriceUpdate (price, previous_price, direction)
      - a session-open reference price, captured on first observation
      - a bounded rolling history of (timestamp, price) points
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._session_open: dict[str, float] = {}
        self._history: dict[str, deque[tuple[float, float]]] = {}
        self._lock = Lock()
        self._version: int = 0  # Monotonically increasing; bumped on every update

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Record a new price for a ticker. Returns the created PriceUpdate.

        On the first observation of a ticker in this process's lifetime, the
        rounded price becomes that ticker's `session_open` reference — used
        to compute `change_percent` for every subsequent update, so change %
        stays stable across client reloads (the reference lives here, not on
        any one client).
        """
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price
            rounded_price = round(price, 2)

            session_open = self._session_open.setdefault(ticker, rounded_price)

            update = PriceUpdate(
                ticker=ticker,
                price=rounded_price,
                previous_price=round(previous_price, 2),
                session_open=session_open,
                timestamp=ts,
            )
            self._prices[ticker] = update

            history = self._history.setdefault(ticker, deque(maxlen=HISTORY_MAXLEN))
            history.append((ts, rounded_price))

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

    def get_history(self, ticker: str) -> list[tuple[float, float]]:
        """Rolling (timestamp, price) history for a ticker, oldest first.

        Empty list if the ticker has never been observed. Used to backfill
        sparklines and the main chart on load; the client then extends the
        series live from SSE.
        """
        with self._lock:
            return list(self._history.get(ticker, ()))

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache (e.g., watchlist removal with no open position).

        Clears the price, session-open reference, and history. If the ticker
        is tracked again later, it starts a fresh session (new session_open,
        empty history) — treated as a new observation window rather than a
        resumption of the old one.
        """
        with self._lock:
            self._prices.pop(ticker, None)
            self._session_open.pop(ticker, None)
            self._history.pop(ticker, None)

    @property
    def version(self) -> int:
        """Current version counter. Useful for SSE change detection."""
        with self._lock:
            return self._version

    def __len__(self) -> int:
        with self._lock:
            return len(self._prices)

    def __contains__(self, ticker: str) -> bool:
        with self._lock:
            return ticker in self._prices
```

### Why a version counter (unchanged)

The SSE loop polls the cache every ~500ms. The version counter lets it skip
sends when nothing changed (relevant when Massive is the source and only
updates every 15s):

```python
last_version = -1
while True:
    if price_cache.version != last_version:
        last_version = price_cache.version
        yield format_sse(price_cache.get_all())
    await asyncio.sleep(0.5)
```

### Why history lives in the cache, not SQLite

Per `PLAN.md` §6: per-tick database writes at 500ms would add latency and
I/O pressure for no durability benefit the project needs — the ring buffer
resets on restart by design, and charts simply backfill from
`get_history()` on connect and extend live via SSE. The durable time series
the project actually needs (`portfolio_snapshots`, written every 30s and on
trade) is unaffected and lives in SQLite as specified in `PLAN.md` §7.

### Memory bound

`HISTORY_MAXLEN = 600` points/ticker × ~40 bytes/tuple × up to a few dozen
tracked tickers (watchlist ∪ open positions) is a few hundred KB — negligible,
and bounded regardless of process uptime.

---

## 5. Abstract Interface

**File: `backend/app/market/interface.py`** — `[existing, unchanged]`

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never calls the data source directly for prices —
    it reads from the cache.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        # ... app runs ...
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        # ... app shutting down ...
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers.

        Starts a background task that periodically writes to the PriceCache.
        Must be called exactly once. Calling start() twice is undefined behavior.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task and release resources.

        Safe to call multiple times. After stop(), the source will not write
        to the cache again.
        """

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. No-op if already present.

        The next update cycle will include this ticker.
        """

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set. No-op if not present.

        Also removes the ticker from the PriceCache.
        """

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

This push model decouples timing: the simulator ticks at 500ms, Massive polls
at 15s, but SSE and the history endpoint always read from the cache at their
own cadence. Neither needs to know which implementation is active.

---

## 6. Seed Prices & Ticker Parameters

**File: `backend/app/market/seed_prices.py`** — `[existing, unchanged]`

Constants only. Shared by the simulator (initial prices + GBM parameters).

```python
"""Seed prices and per-ticker parameters for the market simulator."""

# Realistic starting prices for the default watchlist (as of project creation)
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
}

# Per-ticker GBM parameters
# sigma: annualized volatility (higher = more price movement)
# mu: annualized drift / expected return
TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL": {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT": {"sigma": 0.20, "mu": 0.05},
    "AMZN": {"sigma": 0.28, "mu": 0.05},
    "TSLA": {"sigma": 0.50, "mu": 0.03},  # High volatility
    "NVDA": {"sigma": 0.40, "mu": 0.08},  # High volatility, strong drift
    "META": {"sigma": 0.30, "mu": 0.05},
    "JPM": {"sigma": 0.18, "mu": 0.04},  # Low volatility (bank)
    "V": {"sigma": 0.17, "mu": 0.04},  # Low volatility (payments)
    "NFLX": {"sigma": 0.35, "mu": 0.05},
}

# Default parameters for tickers not in the list above (dynamically added).
# Combined with a deterministic hash-derived seed price (§7.1), any
# well-formed symbol "just works" without a hand-authored entry (PLAN.md §6).
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

# Correlation groups for the simulator's Cholesky decomposition
# Tickers in the same group have higher intra-group correlation
CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech": {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

# Correlation coefficients
INTRA_TECH_CORR = 0.6  # Tech stocks move together
INTRA_FINANCE_CORR = 0.5  # Finance stocks move together
CROSS_GROUP_CORR = 0.3  # Between sectors / unknown tickers
TSLA_CORR = 0.3  # TSLA does its own thing
```

> **Note on determinism (§7.1 below).** `PLAN.md` §6 requires that an unknown
> ticker's default seed price be "deterministic ... stable across restarts."
> The current implementation (`random.uniform(50.0, 300.0)` in
> `GBMSimulator._add_ticker_internal`) is **not** deterministic — a restart
> reseeds Python's global RNG and produces a different price for the same
> unknown ticker. §7.1 replaces this with a hash-derived seed. This is the one
> behavioral fix bundled into this design alongside the additive extensions.

---

## 7. GBM Simulator

**File: `backend/app/market/simulator.py`** — `[existing, with the §7.1 fix]`

Two classes: `GBMSimulator` (pure math engine, stateful) and
`SimulatorDataSource` (the `MarketDataSource` implementation wrapping it in an
async loop).

### 7.1 GBMSimulator — The Math Engine

```python
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import random

import numpy as np

from .cache import PriceCache
from .interface import MarketDataSource
from .seed_prices import (
    CORRELATION_GROUPS,
    CROSS_GROUP_CORR,
    DEFAULT_PARAMS,
    INTRA_FINANCE_CORR,
    INTRA_TECH_CORR,
    SEED_PRICES,
    TICKER_PARAMS,
    TSLA_CORR,
)

logger = logging.getLogger(__name__)


def _default_seed_price(ticker: str) -> float:
    """Deterministic default seed price for a ticker with no curated entry.

    Derived from a stable hash of the symbol so the same unknown ticker
    always gets the same starting price across restarts (PLAN.md §6), while
    still spreading tickers across a realistic $50-$300 range.
    """
    digest = hashlib.sha256(ticker.encode()).hexdigest()
    fraction = int(digest[:8], 16) / 0xFFFFFFFF  # -> [0, 1)
    return round(50.0 + fraction * 250.0, 2)


class GBMSimulator:
    """Geometric Brownian Motion simulator for correlated stock prices.

    Math:
        S(t+dt) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)

    Where:
        S(t)   = current price
        mu     = annualized drift (expected return)
        sigma  = annualized volatility
        dt     = time step as fraction of a trading year
        Z      = correlated standard normal random variable

    The tiny dt (~8.5e-8 for 500ms ticks over 252 trading days * 6.5h/day)
    produces sub-cent moves per tick that accumulate naturally over time.
    """

    # 500ms expressed as a fraction of a trading year
    # 252 trading days * 6.5 hours/day * 3600 seconds/hour = 5,896,800 seconds
    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR  # ~8.48e-8

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability

        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    # --- Public API ---

    def step(self) -> dict[str, float]:
        """Advance all tickers by one time step. Returns {ticker: new_price}.

        This is the hot path — called every 500ms. Keep it fast.
        """
        n = len(self._tickers)
        if n == 0:
            return {}

        z_independent = np.random.standard_normal(n)
        z_correlated = self._cholesky @ z_independent if self._cholesky is not None else z_independent

        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            params = self._params[ticker]
            mu = params["mu"]
            sigma = params["sigma"]

            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z_correlated[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random event: ~0.1% chance per tick per ticker
            # With 10 tickers at 2 ticks/sec, expect an event ~every 50 seconds
            if random.random() < self._event_prob:
                shock_magnitude = random.uniform(0.02, 0.05)
                shock_sign = random.choice([-1, 1])
                self._prices[ticker] *= 1 + shock_magnitude * shock_sign
                logger.debug(
                    "Random event on %s: %.1f%% %s",
                    ticker,
                    shock_magnitude * 100,
                    "up" if shock_sign > 0 else "down",
                )

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the simulation. Rebuilds the correlation matrix."""
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the simulation. Rebuilds the correlation matrix."""
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        """Current price for a ticker, or None if not tracked."""
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        """Return the list of currently tracked tickers."""
        return list(self._tickers)

    # --- Internals ---

    def _add_ticker_internal(self, ticker: str) -> None:
        """Add a ticker without rebuilding Cholesky (for batch initialization)."""
        if ticker in self._prices:
            return
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker, _default_seed_price(ticker))
        self._params[ticker] = TICKER_PARAMS.get(ticker, dict(DEFAULT_PARAMS))

    def _rebuild_cholesky(self) -> None:
        """Rebuild the Cholesky decomposition of the ticker correlation matrix.

        Called whenever tickers are added or removed. O(n^2) but n < 50.
        """
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return

        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                rho = self._pairwise_correlation(self._tickers[i], self._tickers[j])
                corr[i, j] = rho
                corr[j, i] = rho

        self._cholesky = np.linalg.cholesky(corr)

    @staticmethod
    def _pairwise_correlation(t1: str, t2: str) -> float:
        """Determine correlation between two tickers based on sector grouping.

        Correlation structure:
          - Same tech sector:    0.6
          - Same finance sector: 0.5
          - TSLA with anything:  0.3 (it does its own thing)
          - Cross-sector / unknown: 0.3
        """
        tech = CORRELATION_GROUPS["tech"]
        finance = CORRELATION_GROUPS["finance"]

        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR
        if t1 in tech and t2 in tech:
            return INTRA_TECH_CORR
        if t1 in finance and t2 in finance:
            return INTRA_FINANCE_CORR
        return CROSS_GROUP_CORR
```

### 7.2 SimulatorDataSource — Async Wrapper

**`[existing, unchanged]**

```python
class SimulatorDataSource(MarketDataSource):
    """MarketDataSource backed by the GBM simulator.

    Runs a background asyncio task that calls GBMSimulator.step() every
    `update_interval` seconds and writes results to the PriceCache.
    """

    def __init__(
        self,
        price_cache: PriceCache,
        update_interval: float = 0.5,
        event_probability: float = 0.001,
    ) -> None:
        self._cache = price_cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(tickers=tickers, event_probability=self._event_prob)
        # Seed the cache with initial prices so SSE/history have data immediately
        for ticker in tickers:
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
        logger.info("Simulator started with %d tickers", len(tickers))

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Simulator stopped")

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
            logger.info("Simulator: added ticker %s", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)
        logger.info("Simulator: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self) -> None:
        """Core loop: step the simulation, write to cache, sleep."""
        while True:
            try:
                if self._sim:
                    prices = self._sim.step()
                    for ticker, price in prices.items():
                        self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

### Key behaviors

- **Immediate seeding**: `start()` populates the cache — and therefore
  `session_open` and the first history point — *before* the loop begins, so
  SSE and the history endpoint have data on their very first read.
- **Graceful cancellation / exception resilience**: unchanged from the
  existing implementation.

---

## 8. Massive API Client

**File: `backend/app/market/massive_client.py`** — `[existing, unchanged]`

Polls the Massive (Polygon.io) REST snapshot endpoint on a configurable
interval. The synchronous client runs in `asyncio.to_thread()` to avoid
blocking the event loop.

```python
from __future__ import annotations

import asyncio
import logging

from massive import RESTClient
from massive.rest.models import SnapshotMarketType

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveDataSource(MarketDataSource):
    """MarketDataSource backed by the Massive (Polygon.io) REST API.

    Polls GET /v2/snapshot/locale/us/markets/stocks/tickers for all watched
    tickers in a single API call, then writes results to the PriceCache.

    Rate limits:
      - Free tier: 5 req/min → poll every 15s (default)
      - Paid tiers: higher limits → poll every 2-5s
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client: RESTClient | None = None

    async def start(self, tickers: list[str]) -> None:
        self._client = RESTClient(api_key=self._api_key)
        self._tickers = list(tickers)

        # Do an immediate first poll so the cache has data right away
        await self._poll_once()

        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")
        logger.info(
            "Massive poller started: %d tickers, %.1fs interval",
            len(tickers),
            self._interval,
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None
        logger.info("Massive poller stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            logger.info("Massive: added ticker %s (will appear on next poll)", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)
        logger.info("Massive: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    # --- Internal ---

    async def _poll_loop(self) -> None:
        """Poll on interval. First poll already happened in start()."""
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        """Execute one poll cycle: fetch snapshots, update cache."""
        if not self._tickers or not self._client:
            return

        try:
            snapshots = await asyncio.to_thread(self._fetch_snapshots)
            processed = 0
            for snap in snapshots:
                try:
                    price = snap.last_trade.price
                    timestamp = snap.last_trade.timestamp / 1000.0  # ms -> s
                    self._cache.update(ticker=snap.ticker, price=price, timestamp=timestamp)
                    processed += 1
                except (AttributeError, TypeError) as e:
                    logger.warning(
                        "Skipping snapshot for %s: %s", getattr(snap, "ticker", "???"), e
                    )
            logger.debug("Massive poll: updated %d/%d tickers", processed, len(self._tickers))

        except Exception as e:
            logger.error("Massive poll failed: %s", e)
            # Don't re-raise — the loop retries on the next interval.
            # Common failures: 401 (bad key), 429 (rate limit), network errors.

    def _fetch_snapshots(self) -> list:
        """Synchronous call to the Massive REST API. Runs in a thread."""
        return self._client.get_snapshot_all(
            market_type=SnapshotMarketType.STOCKS,
            tickers=self._tickers,
        )
```

### Error handling philosophy (unchanged)

| Error | Behavior |
|---|---|
| 401 Unauthorized | Logged as error; poller keeps retrying. |
| 429 Rate limited | Logged; retried on next interval. |
| Network timeout | Logged; retried on next cycle. |
| Malformed snapshot | That ticker skipped with a warning; others processed. |
| All tickers fail | Cache retains last-known values — including `session_open` and history, which are untouched by a failed poll. SSE keeps streaming stale-but-present data. |

---

## 9. Factory

**File: `backend/app/market/factory.py`** — `[existing, unchanged]`

```python
from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
```

---

## 10. SSE Streaming Endpoint

**File: `backend/app/market/stream.py`** — `[modified: payload now includes `session_open`; logic unchanged]`

```python
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request

from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the market-data router: SSE price stream + history REST endpoint.

    Factory pattern injects the PriceCache without module-level globals, and
    avoids double route registration if ever called more than once (each
    call gets a fresh APIRouter instead of sharing a module-level instance).
    """
    router = APIRouter(tags=["market-data"])

    @router.get("/api/stream/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        """SSE endpoint for live price updates.

        Streams all tracked ticker prices every ~500ms. The client connects
        with EventSource and receives events shaped like:

            data: {"AAPL": {"ticker": "AAPL", "price": 190.50, ...}, ...}

        Includes a retry directive so the browser auto-reconnects on
        disconnection (EventSource's built-in behavior).
        """
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
            },
        )

    @router.get("/api/prices/{ticker}/history")
    async def price_history(ticker: str) -> dict:
        """Recent in-memory price history for a ticker.

        Backfills sparklines (watchlist) and the main chart (on ticker
        selection) so they render already-populated, then callers extend the
        series live from the SSE stream. 404s if the ticker has never been
        observed by the running process (unknown ticker, or tracking just
        started and the first tick hasn't landed yet).
        """
        ticker = ticker.upper().strip()
        points = price_cache.get_history(ticker)
        if not points:
            raise HTTPException(status_code=404, detail=f"No price history for {ticker}")
        return {
            "ticker": ticker,
            "points": [{"timestamp": ts, "price": price} for ts, price in points],
        }

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted price events.

    Sends all prices every `interval` seconds, only when the cache version
    has changed. Stops when the client disconnects.
    """
    yield "retry: 1000\n\n"

    last_version = -1
    client_ip = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client_ip)

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client_ip)
                break

            current_version = price_cache.version
            if current_version != last_version:
                last_version = current_version
                prices = price_cache.get_all()

                if prices:
                    data = {ticker: update.to_dict() for ticker, update in prices.items()}
                    yield f"data: {json.dumps(data)}\n\n"

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client_ip)
```

### SSE wire format

```
data: {"AAPL":{"ticker":"AAPL","price":190.50,"previous_price":190.42,"session_open":189.80,"timestamp":1707580800.5,"change":0.08,"change_percent":0.3688,"direction":"up"},"GOOGL":{...}}

```

```javascript
const eventSource = new EventSource('/api/stream/prices');
eventSource.onmessage = (event) => {
  const prices = JSON.parse(event.data);
  // prices["AAPL"].change_percent  -> stable "day change %" for display
  // prices["AAPL"].direction       -> drives the CSS flash color
};
```

### Why this endpoint moved out of a module-level router

The original design created a module-level `router = APIRouter(...)` and
registered `/prices` on it inside the factory closure — a latent footgun if
`create_stream_router()` is ever called twice (e.g., once per test), which
would double-register the route. This design creates a fresh `APIRouter`
inside the factory function instead, so each call is fully independent.

---

## 11. Price History REST Endpoint

Already shown in §10 as part of the same router (`GET
/api/prices/{ticker}/history`) — kept in `stream.py` alongside the SSE
endpoint because both are thin reads over `PriceCache` with no other
dependencies. Documented separately here because it satisfies a distinct
requirement from `PLAN.md` §8:

| Method | Path | Description |
|---|---|---|
| GET | `/api/prices/{ticker}/history` | Recent in-memory price history for a ticker (backfills charts/sparklines on load) |

**Response shape:**

```json
{
  "ticker": "AAPL",
  "points": [
    {"timestamp": 1707580800.0, "price": 189.80},
    {"timestamp": 1707580800.5, "price": 189.83},
    {"timestamp": 1707580801.0, "price": 189.79}
  ]
}
```

**Client usage** — sparkline backfill on watchlist load, and main-chart
backfill on ticker selection, both followed by live extension from SSE:

```javascript
async function loadHistory(ticker) {
  const res = await fetch(`/api/prices/${ticker}/history`);
  if (!res.ok) return [];               // unknown/untracked ticker — start empty
  const { points } = await res.json();
  return points;                        // seed the chart; SSE appends from here
}
```

**404 semantics.** A 404 means "no history yet," which is a normal transient
state right after a ticker is added (simulator seeds it immediately, so this
window is essentially zero; Massive may have a brief gap before its first
poll lands) — not an error condition the frontend needs to surface loudly.

---

## 12. Tracked Ticker Set — Watchlist ∪ Positions

`PLAN.md` §6 defines the tracked set as **the union of the watchlist and
every ticker with an open position**, not the watchlist alone — a user can
sell part of a holding, remove that ticker from the watchlist, and still own
shares that need a live price for portfolio valuation. This is a
coordination rule that the market data layer's callers (watchlist and trade
routes, in the not-yet-built `backend/app/routes/` layer) must follow; the
market data layer itself just exposes `add_ticker`/`remove_ticker` and does
not know about the database.

### Contract each caller must honor

```python
# On watchlist add (POST /api/watchlist):
#   always call source.add_ticker(ticker) — idempotent, no-op if already tracked

# On watchlist remove (DELETE /api/watchlist/{ticker}):
#   only call source.remove_ticker(ticker) if no open position remains
async def remove_from_watchlist(ticker: str, db, source: MarketDataSource) -> None:
    await db.delete_watchlist_entry(ticker)
    position = await db.get_position(ticker)
    if position is None or position.quantity == 0:
        await source.remove_ticker(ticker)
    # else: ticker stays tracked — still needed for portfolio valuation

# On opening a new position via trade (not previously on the watchlist):
#   always call source.add_ticker(ticker) — the position now needs a live price
async def execute_trade(trade, db, source: MarketDataSource, price_cache: PriceCache) -> None:
    price = price_cache.get_price(trade.ticker)
    if price is None:
        raise HTTPException(400, f"Price not yet available for {trade.ticker}")
    # ... validate + apply trade to db (§8 of PLAN.md) ...
    await source.add_ticker(trade.ticker)  # no-op if already tracked

# On a sell that fully closes a position:
#   drop tracking only if the ticker isn't also on the watchlist
async def after_sell_closes_position(ticker: str, db, source: MarketDataSource) -> None:
    on_watchlist = await db.get_watchlist_entry(ticker)
    if on_watchlist is None:
        await source.remove_ticker(ticker)
```

`add_ticker`/`remove_ticker` on both `SimulatorDataSource` and
`MassiveDataSource` are already idempotent no-ops when the ticker is already
in (or absent from) the tracked set, so callers can invoke them
unconditionally on the "add" side without checking first — only the
"remove" side needs the position/watchlist cross-check shown above.

---

## 13. FastAPI Lifecycle Integration

The market data system starts and stops with the FastAPI app via the
`lifespan` context manager. Per `PLAN.md` §7, the database must be
initialized **before** the market-data task starts, so the initial tracked
set (watchlist ∪ open positions) is available at boot with no lazy
first-request gap.

**In `backend/app/main.py` (not yet created — this is its target shape):**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db, load_tracked_tickers  # DB layer, not yet built
from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.stream import create_stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---

    # 1. Initialize + seed the database first (PLAN.md §7) — schema creation
    #    and default watchlist seeding happen here, before anything reads it.
    await init_db()

    # 2. Create the shared price cache and data source.
    price_cache = PriceCache()
    app.state.price_cache = price_cache
    source = create_market_data_source(price_cache)
    app.state.market_source = source

    # 3. Load the initial tracked set: watchlist ∪ open positions (§12).
    initial_tickers = await load_tracked_tickers()
    await source.start(initial_tickers)

    # 4. Register the market-data router (SSE stream + history endpoint).
    app.include_router(create_stream_router(price_cache))

    yield  # App is running

    # --- SHUTDOWN ---
    await source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)


def get_price_cache() -> PriceCache:
    return app.state.price_cache


def get_market_source():
    return app.state.market_source
```

### Accessing market data from other routes

```python
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api")


@router.post("/portfolio/trade")
async def execute_trade(
    trade: TradeRequest,
    price_cache: PriceCache = Depends(get_price_cache),
    source=Depends(get_market_source),
):
    current_price = price_cache.get_price(trade.ticker)
    if current_price is None:
        raise HTTPException(404, f"No price available for {trade.ticker}")
    # ... validate + apply trade (§8 of PLAN.md) ...
    await source.add_ticker(trade.ticker)  # ensure it's tracked post-trade (§12)
```

---

## 14. Testing Strategy

The existing suite (`backend/tests/market/`, 73 tests) covers `models.py`,
`cache.py`, `interface.py` (via subclasses), `simulator.py`, `factory.py`, and
`massive_client.py` — see `MARKET_DATA_SUMMARY.md` for current pass/coverage
numbers. New tests needed for the extensions in this document:

### 14.1 `PriceCache` — session open + history

```python
class TestPriceCacheExtensions:

    def test_session_open_set_on_first_update(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.00)
        assert update.session_open == 190.00

    def test_session_open_stable_across_updates(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("AAPL", 195.00)
        update = cache.update("AAPL", 185.00)
        assert update.session_open == 190.00  # unchanged since first observation

    def test_change_percent_uses_session_open_not_previous(self):
        cache = PriceCache()
        cache.update("AAPL", 100.00)
        cache.update("AAPL", 110.00)
        update = cache.update("AAPL", 105.00)
        # vs session_open (100), not vs previous_price (110)
        assert update.change_percent == 5.0
        # tick-over-tick change is still vs previous_price
        assert update.direction == "down"

    def test_history_accumulates(self):
        cache = PriceCache()
        for price in [190.0, 191.0, 192.0]:
            cache.update("AAPL", price)
        history = cache.get_history("AAPL")
        assert [p for _, p in history] == [190.0, 191.0, 192.0]

    def test_history_bounded_by_maxlen(self):
        cache = PriceCache()
        for i in range(HISTORY_MAXLEN + 50):
            cache.update("AAPL", 100.0 + i * 0.01)
        assert len(cache.get_history("AAPL")) == HISTORY_MAXLEN

    def test_remove_clears_session_open_and_history(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.remove("AAPL")
        assert cache.get_history("AAPL") == []
        # Re-adding starts a fresh session
        update = cache.update("AAPL", 200.00)
        assert update.session_open == 200.00
```

### 14.2 Deterministic default seed price

```python
class TestDefaultSeedPrice:

    def test_unknown_ticker_price_is_deterministic(self):
        sim1 = GBMSimulator(tickers=["ZZZZ"])
        sim2 = GBMSimulator(tickers=["ZZZZ"])
        assert sim1.get_price("ZZZZ") == sim2.get_price("ZZZZ")

    def test_unknown_ticker_price_in_range(self):
        sim = GBMSimulator(tickers=["ZZZZ"])
        assert 50.0 <= sim.get_price("ZZZZ") <= 300.0

    def test_different_unknown_tickers_differ(self):
        sim = GBMSimulator(tickers=["ZZZZ", "YYYY"])
        assert sim.get_price("ZZZZ") != sim.get_price("YYYY")
```

### 14.3 History REST endpoint (ASGI integration test)

```python
import pytest
from httpx import AsyncClient, ASGITransport

from app.market.cache import PriceCache
from app.market.stream import create_stream_router


@pytest.mark.asyncio
async def test_price_history_endpoint():
    from fastapi import FastAPI

    cache = PriceCache()
    cache.update("AAPL", 190.00)
    cache.update("AAPL", 191.00)

    app = FastAPI()
    app.include_router(create_stream_router(cache))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/prices/AAPL/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "AAPL"
        assert len(body["points"]) == 2


@pytest.mark.asyncio
async def test_price_history_404_for_unknown_ticker():
    from fastapi import FastAPI

    cache = PriceCache()
    app = FastAPI()
    app.include_router(create_stream_router(cache))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/prices/ZZZZ/history")
        assert resp.status_code == 404
```

---

## 15. Error Handling & Edge Cases

Carried over from the existing design (empty watchlist at startup, price
cache miss during trade, invalid Massive API key, thread safety under load,
simulator numerical precision — see `planning/archive/MARKET_DATA_DESIGN.md`
§13 for the full writeups, unchanged). Additional cases introduced by this
document's extensions:

### 15.1 History requested for a ticker removed mid-session

If a ticker is removed from tracking (§12) between a client's initial page
load and a later re-fetch of `/api/prices/{ticker}/history`, the endpoint
now 404s (history was cleared in `PriceCache.remove()`). This is correct:
the ticker is no longer tracked, so there is nothing current to backfill.
The frontend should stop rendering that ticker's chart/sparkline once it
disappears from an SSE payload or a watchlist/portfolio response, rather
than continuing to poll history for it.

### 15.2 Session-open reference and a restarted process

`session_open` is captured fresh on first observation **per process
lifetime** — a container restart resets every ticker's reference, and
`change_percent` starts over from whatever price is first observed after
restart. This matches real trading terminals (change vs. the session's open,
not an all-time reference) and is consistent with `PLAN.md`'s framing of it
as a "session reference (open) price."

### 15.3 Re-adding a previously-tracked ticker

Per §4's `remove()` docstring: removing then re-adding a ticker (watchlist
remove → later re-add, with no position keeping it alive in between) starts
a brand-new session — new `session_open`, empty history. This is a
deliberate simplification: there is no server-side concept of "pause and
resume" for a ticker's session, only "tracked" or "not tracked."

---

## 16. Configuration Summary

| Parameter | Location | Default | Description |
|---|---|---|---|
| `MASSIVE_API_KEY` | Environment variable | `""` (empty) | If set, use Massive API; otherwise use simulator |
| `update_interval` | `SimulatorDataSource.__init__` | `0.5` (seconds) | Time between simulator ticks |
| `poll_interval` | `MassiveDataSource.__init__` | `15.0` (seconds) | Time between Massive API polls |
| `event_probability` | `GBMSimulator.__init__` | `0.001` | Chance of a random shock event per ticker per tick |
| `dt` | `GBMSimulator.__init__` | `~8.5e-8` | GBM time step (fraction of a trading year) |
| `HISTORY_MAXLEN` | `cache.py` | `600` (points) | Rolling history length per ticker (~5 min at 500ms cadence) |
| SSE push interval | `_generate_events()` | `0.5` (seconds) | Time between SSE pushes to the client |
| SSE retry directive | `_generate_events()` | `1000` (ms) | Browser EventSource reconnection delay |

### Package `__init__.py`

**File: `backend/app/market/__init__.py`** — unchanged shape, still re-exports
the same five names (`PriceCache`'s and `PriceUpdate`'s new fields are part of
their existing exported classes, not new exports):

```python
"""Market data subsystem for FinAlly.

Public API:
    PriceUpdate         - Immutable price snapshot dataclass
    PriceCache          - Thread-safe in-memory price store (+ session open, history)
    MarketDataSource    - Abstract interface for data providers
    create_market_data_source - Factory that selects simulator or Massive
    create_stream_router - FastAPI router factory for SSE + history endpoints
"""

from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import PriceUpdate
from .stream import create_stream_router

__all__ = [
    "PriceUpdate",
    "PriceCache",
    "MarketDataSource",
    "create_market_data_source",
    "create_stream_router",
]
```

---

## 17. Implementation Checklist

Concrete diff from the current, already-built state to the design in this
document:

1. **`models.py`** — add `session_open: float` field to `PriceUpdate`; change
   `change_percent` to compute against `session_open` instead of
   `previous_price`; add `session_open` to `to_dict()`.
2. **`cache.py`** — add `_session_open: dict[str, float]` and
   `_history: dict[str, deque]` state; `update()` sets `session_open` via
   `setdefault` and appends to history; add `get_history(ticker)`; `remove()`
   clears both new dicts alongside `_prices`; add module-level
   `HISTORY_MAXLEN = 600`.
3. **`simulator.py`** — replace `random.uniform(50.0, 300.0)` in
   `_add_ticker_internal` with a deterministic `_default_seed_price(ticker)`
   (hash-derived) so unknown-ticker seed prices survive restarts, per
   `PLAN.md` §6.
4. **`stream.py`** — add `GET /api/prices/{ticker}/history` to the router
   returned by `create_stream_router()`; switch from a module-level `router`
   to a fresh `APIRouter()` per call (removes the double-registration
   footgun noted in the prior review).
5. **Tests** — add the cases in §14.1–14.3 to
   `backend/tests/market/test_cache.py`, `test_simulator.py`, and a new
   `test_stream.py` (the existing suite has no SSE/HTTP integration test;
   `httpx.AsyncClient` + `ASGITransport` is the minimal way to add one).
6. **Downstream (not part of this module, but depends on it)** — when
   `backend/app/main.py` and the watchlist/trade routes are built, they must
   follow the tracked-ticker-set contract in §12 and the startup ordering in
   §13 (DB init → cache/source creation → `source.start(tracked_tickers)` →
   router registration).

Everything else in the current implementation (`interface.py`,
`seed_prices.py` besides the seed-price fix, `massive_client.py`,
`factory.py`, the GBM math itself, correlation structure, error handling) is
unchanged and carries forward as-is.
