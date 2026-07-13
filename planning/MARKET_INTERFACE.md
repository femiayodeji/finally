# Market Data Interface

The unified Python API for retrieving stock prices in FinAlly. One contract, two
implementations: the **Massive** REST client when `MASSIVE_API_KEY` is set, the
**GBM simulator** otherwise. Everything downstream of the price cache is agnostic to
which one is running.

- **Massive client** details: `MASSIVE_API.md`
- **Simulator** details: `MARKET_SIMULATOR.md`
- **Design authority**: `PLAN.md` §3 (backend owns the core), §6 (market data)

---

## 1. Design goals

| Goal | How the interface delivers it |
|------|-------------------------------|
| **Source-agnostic** | Downstream code reads a `PriceCache`; it never touches the source. |
| **Swappable at boot** | A factory picks the implementation from one env var. No other code branches on it. |
| **Backend owns the core** (§3) | Price, change %, and history are computed/held server-side. The frontend renders; it never derives these. |
| **Scale seam** | The cache is the single seam that later becomes a shared store (Redis) for multi-user, with no change to sources or consumers. |
| **Speed** | In-process background task + in-memory cache + SSE push. No per-read network or DB hit. |

The core rule: **producers write to the cache; consumers read from the cache; the two
never call each other directly.** The cache is the contract between them.

---

## 2. Architecture

```
                     create_market_data_source(cache)   ← reads MASSIVE_API_KEY
                                  │  picks one
        ┌─────────────────────────┴─────────────────────────┐
        ▼                                                     ▼
 SimulatorDataSource                                  MassiveDataSource
 (GBM background task, ~500ms)                 (REST poller, 2–15s, one call/cycle)
        │                                                     │
        └──────────────────────┬──────────────────────────────┘
                               ▼  writes PriceUpdate
                         ┌───────────┐
                         │ PriceCache│  ← single source of truth (thread-safe)
                         └───────────┘  latest · session-ref · rolling history · change %
                               │  reads
        ┌──────────────────────┼──────────────────────┬───────────────────┐
        ▼                      ▼                      ▼                   ▼
 SSE /api/stream/prices   Portfolio valuation   Trade execution   /api/prices/{t}/history
```

Both sources implement the same `MarketDataSource` ABC and push into the same
`PriceCache`. The factory is the *only* place that knows both concrete types exist.

Actual layout (`backend/app/market/`):

| Module | Role |
|--------|------|
| `models.py` | `PriceUpdate` — immutable per-tick snapshot |
| `cache.py` | `PriceCache` — thread-safe store, the single source of truth |
| `interface.py` | `MarketDataSource` — the ABC both sources implement |
| `simulator.py` | `GBMSimulator` + `SimulatorDataSource` |
| `massive_client.py` | `MassiveDataSource` |
| `seed_prices.py` | Seed prices, GBM params, correlation groups |
| `factory.py` | `create_market_data_source(cache)` — env-driven selection |
| `stream.py` | `create_stream_router(cache)` — FastAPI SSE endpoint |

---

## 3. The contract: `MarketDataSource`

An abstract base class. A source produces prices for a mutable ticker set and writes
them into an injected `PriceCache`. Consumers never see this object.

```python
from abc import ABC, abstractmethod

class MarketDataSource(ABC):
    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing updates for `tickers`. Starts one background task.
        Called exactly once at app startup, after the DB seed is read."""

    @abstractmethod
    async def stop(self) -> None:
        """Cancel the background task and release resources. Idempotent."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add to the tracked set. No-op if present. Seeds a price promptly."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove from the tracked set and drop it from the cache."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Current tracked set."""
```

**Lifecycle**

```python
cache  = PriceCache()
source = create_market_data_source(cache)      # unstarted
await source.start(seed_watchlist_union_positions)
# ... running: watchlist / position changes drive add/remove ...
await source.add_ticker("TSLA")
await source.remove_ticker("GOOGL")            # only if no open position (§6)
# ... shutdown ...
await source.stop()
```

**Contract guarantees each implementation must honor**

- `start` runs a *single* background task and returns immediately (non-blocking).
- Prices are seeded into the cache for the initial set before/at `start` return, so
  the first SSE frame and the first portfolio valuation have data — no cold gap.
- `add_ticker` / `remove_ticker` are safe to call concurrently with the running task.
- `stop` is idempotent and leaves no orphaned task.
- The **tracked set = watchlist ∪ open positions** (§6). The caller composes that
  union; the source just tracks what it's told. `remove_ticker` is issued only when a
  ticker leaves *both* sets.

---

## 4. `PriceCache` — the single source of truth

Thread-safe, in-memory, `Lock`-guarded. Producers call `update`; consumers call the
getters. A monotonic `version` counter lets the SSE loop detect changes cheaply.

```python
class PriceCache:
    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate: ...
    def get(self, ticker: str) -> PriceUpdate | None: ...
    def get_price(self, ticker: str) -> float | None: ...
    def get_all(self) -> dict[str, PriceUpdate]: ...          # shallow copy
    def remove(self, ticker: str) -> None: ...
    @property
    def version(self) -> int: ...                             # bumped on every update
```

Why the cache is the seam (§3):

- **Scalability** — swap the in-memory dict for Redis and neither the sources nor the
  SSE/portfolio/trade consumers change. The method surface is the boundary.
- **Consistency** — every SSE client, every browser tab, portfolio valuation, and
  trade execution read the *same* authoritative numbers.
- **Security** — money math and validation happen server-side against cache prices;
  the client never supplies or computes a price.

### `PriceUpdate` (the record)

Immutable, `frozen=True, slots=True`. One ticker at one instant.

```python
@dataclass(frozen=True, slots=True)
class PriceUpdate:
    ticker: str
    price: float
    previous_price: float
    timestamp: float                # Unix seconds
    # properties: change, change_percent, direction ("up"/"down"/"flat")
    # to_dict() → JSON for SSE / REST
```

---

## 5. Change %, session reference, and rolling history

`PLAN.md` §3/§6 require the backend to own **change % vs. a session-reference price**
and a **bounded rolling price history**, so every client agrees and charts survive
reloads. These are **additive extensions to `PriceCache`/`PriceUpdate`** on top of the
latest/previous/timestamp core that already exists.

**Session reference (open) price.** On the *first* observation of a ticker after process
start, the cache captures a `session_ref` price. `change_percent` is then computed as
`(price − session_ref) / session_ref × 100` — **not** tick-to-tick — so the number is
stable across reloads and identical for all clients. (The current `PriceUpdate.change_percent`
is tick-over-tick; this is the extension point that moves it to session-ref.)

**Rolling history.** Per ticker, a bounded ring buffer (~600 points ≈ a few minutes at
500 ms). `update` appends; the buffer evicts oldest. Exposed via
`GET /api/prices/{ticker}/history` so charts/sparklines **backfill on load** and then
**extend live from SSE**. History is **in-memory only** — never written to SQLite
(per-tick DB writes would hurt latency; durable time-series is `portfolio_snapshots`).
The buffer resets on restart, which is fine: clients rebackfill on connect.

Both live in the cache layer precisely because the cache is the scale seam — moving to
Redis later carries the ref price and history with it, unchanged for consumers.

---

## 6. The factory — one decision point

```python
import os

def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    return SimulatorDataSource(price_cache=price_cache)
```

- Returns an **unstarted** source; the caller awaits `start(...)`.
- `MASSIVE_API_KEY` set & non-empty ⇒ real data. Absent/empty ⇒ simulator.
- This is the **only** branch on data source in the codebase. Adding a third source
  (e.g. a different vendor) means one new class + one line here — nothing else moves.

---

## 7. How the two implementations satisfy the contract

| Aspect | `SimulatorDataSource` | `MassiveDataSource` |
|--------|-----------------------|----------------------|
| Engine | In-process GBM (`GBMSimulator.step()`) | Massive REST `get_snapshot_all` |
| Cadence | ~500 ms `asyncio.sleep` loop | 2–15 s poll (rate-tier driven) |
| Cost / cycle | CPU only, no I/O | **1** HTTP request for all tickers |
| Blocking? | No | Sync client wrapped in `asyncio.to_thread` |
| `add_ticker` | Rebuilds correlation matrix, seeds price now | Appends to list; appears next poll |
| Failure mode | Guarded `step()`; loop continues | Guarded fetch/parse; loop continues |
| Determinism | Seeded RNG for tests | Live market data |

Both: run a single named `asyncio.Task`, seed the cache on `start`, cancel cleanly on
`stop`, and write **only** through `cache.update(...)`.

---

## 8. Consuming the interface (startup wiring)

```python
from app.market import PriceCache, create_market_data_source, create_stream_router

# --- FastAPI startup (after DB init + seed) ---
cache  = PriceCache()
source = create_market_data_source(cache)          # env-driven
tracked = watchlist_tickers | open_position_tickers  # union, §6
await source.start(sorted(tracked))

app.include_router(create_stream_router(cache))    # GET /api/stream/prices

# --- Reading prices anywhere (portfolio, trades) ---
price = cache.get_price("AAPL")                     # float | None
snap  = cache.get("AAPL")                           # PriceUpdate | None
book  = cache.get_all()                             # dict[str, PriceUpdate]

# --- Watchlist / position changes ---
await source.add_ticker("TSLA")                     # on add or new position
await source.remove_ticker("GOOGL")                 # only if no open position remains

# --- Shutdown ---
await source.stop()
```

Consumers depend only on `PriceCache` and (at startup) the factory + `MarketDataSource`
lifecycle. No consumer imports `SimulatorDataSource` or `MassiveDataSource` directly —
that coupling lives solely in `factory.py`.

---

## 9. Testing the interface

- **Contract tests** run against both sources through the ABC: `start` seeds the cache,
  `add/remove_ticker` mutate `get_tickers()`, `stop` is idempotent and cancels the task.
- **Simulator** is deterministic under a seeded RNG — assert GBM math and correlation.
- **Massive** is tested with a **mocked client** (`_fetch_snapshots` patched): verify
  cache updates, ms→s timestamp conversion, malformed-snapshot skipping, and that API
  exceptions don't crash the poll loop.
- **Factory** is tested by toggling `MASSIVE_API_KEY` and asserting the returned type.

See `MARKET_SIMULATOR.md` for the simulator's internals and `MASSIVE_API.md` for the
REST client and polling pattern.
