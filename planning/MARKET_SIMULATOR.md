# Market Simulator

The built-in price simulator — FinAlly's **default** market data source when no
`MASSIVE_API_KEY` is set. It generates believable, live-updating prices with no
external dependency, so the app "just works" out of the box for the demo.

It sits behind the same `MarketDataSource` contract as the real Massive client
(see `MARKET_INTERFACE.md`), writing into the shared `PriceCache`. Nothing downstream
knows a simulator is running.

- Interface contract: `MARKET_INTERFACE.md`
- Real-data alternative: `MASSIVE_API.md`
- Design authority: `PLAN.md` §6 (Simulator)

---

## 1. What "good" looks like

The simulator has to sell the illusion of a live market on screen. Requirements:

| Property | Why | How |
|----------|-----|-----|
| Realistic starting prices | AAPL should open near ~$190, not $7 | Curated `SEED_PRICES` |
| Continuous small moves | Prices flicker green/red every tick | GBM with tiny `dt` |
| Per-ticker character | TSLA jumpier than JPM | Per-ticker `sigma`/`mu` |
| Correlated sectors | Tech names move together, not randomly | Cholesky-correlated shocks |
| Occasional drama | A sudden 2–5% pop makes the screen feel alive | Random shock events |
| Any symbol works | User/AI can add `PYPL` with no curated entry | Deterministic defaults |
| Deterministic under test | Reproducible assertions | Seedable RNG |
| Fast | Hot path runs every 500 ms | Vectorized NumPy, cheap per step |

---

## 2. The model — Geometric Brownian Motion

Each price follows GBM, the standard model for stock-like random walks. Per step:

```
S(t+dt) = S(t) · exp( (μ − ½σ²)·dt  +  σ·√dt·Z )
```

| Symbol | Meaning |
|--------|---------|
| `S(t)` | current price |
| `μ` (mu) | annualized drift (expected return) |
| `σ` (sigma) | annualized volatility |
| `dt` | time step as a fraction of a trading year |
| `Z` | a **correlated** standard-normal draw |

**Choosing `dt`.** A trading year is `252 days × 6.5 h × 3600 s = 5,896,800 s`.
A 500 ms tick is `0.5 / 5,896,800 ≈ 8.48e-8` of a year. This tiny `dt` yields sub-cent
moves per tick that accumulate naturally — realistic flicker, no wild jumps. The
`exp(...)` form keeps prices strictly positive (they can't cross zero).

```python
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600      # 5,896,800
DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR      # ~8.48e-8

drift     = (mu - 0.5 * sigma**2) * dt
diffusion = sigma * math.sqrt(dt) * z            # z is the correlated draw
new_price = price * math.exp(drift + diffusion)
```

---

## 3. Correlation via Cholesky decomposition

Real sectors move together. Independent random walks would look wrong — NVDA up 1%
while AAPL and MSFT drift the other way on the same tick reads as noise, not a market.

We build a **correlation matrix** `C` over the tracked tickers, factor it as
`C = L·Lᵀ` (Cholesky, `L` lower-triangular), then turn independent normals into
correlated ones:

```python
z_independent = np.random.standard_normal(n)     # n i.i.d. draws
z_correlated  = L @ z_independent                # now correlated per C
```

Pairwise correlation comes from sector grouping (`seed_prices.py`):

| Pair | ρ |
|------|---|
| Same **tech** sector (AAPL, GOOGL, MSFT, AMZN, META, NVDA, NFLX) | **0.6** |
| Same **finance** sector (JPM, V) | **0.5** |
| Cross-sector / unknown ticker | **0.3** |
| Anything involving **TSLA** | **0.3** (it does its own thing) |

`L` is recomputed only when the ticker set changes (`add_ticker`/`remove_ticker`) —
`O(n²)` to build, but `n` is small (<50) and it's off the hot path. `step()` just does
one matrix-vector multiply.

---

## 4. Random shock events

For visual drama, each ticker has a small independent chance per tick of a sudden jump:

```python
if random.random() < event_probability:         # default 0.001 (0.1%)
    magnitude = random.uniform(0.02, 0.05)       # 2–5%
    sign      = random.choice([-1, 1])
    price *= 1 + magnitude * sign
```

With 10 tickers at 2 ticks/s and p=0.001, expect an event roughly every ~50 s — often
enough to notice, rare enough to feel like news rather than chaos.

---

## 5. Seed data & unknown tickers

`seed_prices.py` holds three things:

```python
SEED_PRICES   = {"AAPL": 190.00, "GOOGL": 175.00, "MSFT": 420.00, ... }   # realistic opens
TICKER_PARAMS = {"TSLA": {"sigma": 0.50, "mu": 0.03},                     # per-ticker character
                 "JPM":  {"sigma": 0.18, "mu": 0.04}, ... }
CORRELATION_GROUPS = {"tech": {...}, "finance": {...}}                     # sector membership
```

**Any well-formed symbol works** (PLAN §6). A ticker with no curated entry gets:

- **default GBM params** — `DEFAULT_PARAMS = {"sigma": 0.25, "mu": 0.05}`,
- **cross-sector correlation** (0.3) with everything,
- a **seed price**.

> **Design note — deterministic seed price.** PLAN §6 requires an unknown ticker's seed
> price to be **deterministic and stable across restarts** (derived from the symbol),
> so the same symbol reopens at the same price. The current code uses
> `random.uniform(50, 300)` as the fallback, which is *not* stable across restarts. The
> intended implementation derives it from a hash of the symbol, e.g.:
> ```python
> import hashlib
> def default_seed_price(ticker: str) -> float:
>     h = int(hashlib.sha256(ticker.encode()).hexdigest(), 16)
>     return round(50 + (h % 25000) / 100, 2)   # stable $50–$300
> ```
> This is the one place the simulator should change to fully meet the spec.

---

## 6. Code structure

Two classes in `simulator.py`, split by responsibility:

### `GBMSimulator` — the math engine (no async, no I/O)

Owns prices, params, and the Cholesky factor. Pure and synchronous → trivially testable.

```python
class GBMSimulator:
    def __init__(self, tickers, dt=DEFAULT_DT, event_probability=0.001): ...
    def step(self) -> dict[str, float]:      # advance all tickers one tick → {ticker: price}
    def add_ticker(self, ticker): ...        # add + rebuild Cholesky
    def remove_ticker(self, ticker): ...     # remove + rebuild Cholesky
    def get_price(self, ticker) -> float | None: ...
    def get_tickers(self) -> list[str]: ...
```

`step()` is the hot path: draw `n` normals → correlate via `L` → apply GBM per ticker →
maybe shock → round to cents → return. One vectorized draw + one matmul per tick.

### `SimulatorDataSource` — the async adapter

Implements `MarketDataSource`. Wraps `GBMSimulator` in a background loop and writes to
the `PriceCache`.

```python
class SimulatorDataSource(MarketDataSource):
    def __init__(self, price_cache, update_interval=0.5, event_probability=0.001): ...

    async def start(self, tickers):
        self._sim = GBMSimulator(tickers, event_probability=self._event_prob)
        for t in tickers:                                # seed cache immediately
            self._cache.update(t, self._sim.get_price(t))
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

    async def _run_loop(self):
        while True:
            try:
                for ticker, price in self._sim.step().items():
                    self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")   # never kill the loop
            await asyncio.sleep(self._interval)

    async def add_ticker(self, ticker):    # add to sim, seed price now
    async def remove_ticker(self, ticker): # drop from sim and cache
    async def stop(self):                  # cancel task, idempotent
    def get_tickers(self): ...
```

Key behaviors:

- **Immediate seed** on `start` and on `add_ticker` — the cache never has a hole; SSE's
  first frame and portfolio valuation always have a price.
- **Loop is bulletproof** — a bad `step()` is logged and the loop continues.
- **Clean shutdown** — `stop()` cancels the task and swallows `CancelledError`.

---

## 7. Relationship to the price cache

The simulator writes prices; it does **not** compute change % or history. Those are the
cache's job (PLAN §3, "backend owns the core"):

- `cache.update(ticker, price)` records latest + previous and bumps `version`.
- The cache's **session-reference price** and **rolling history ring buffer** (see
  `MARKET_INTERFACE.md` §5) are populated the same way whether prices come from the
  simulator or Massive — the source is irrelevant to those computations.

This keeps the simulator focused on one thing: producing believable prices.

---

## 8. Testing

The pure `GBMSimulator` makes this straightforward:

- **GBM correctness** — with `sigma≈0`, drift dominates and prices barely move; with a
  fixed seed, `step()` output is reproducible.
- **Positivity** — prices stay `> 0` across many steps (the `exp` form guarantees it).
- **Correlation** — over many steps, sampled tech-pair correlation trends toward 0.6;
  the Cholesky factor of a valid correlation matrix exists (positive-definite).
- **Dynamic set** — `add_ticker`/`remove_ticker` rebuild `L` and update `get_tickers()`.
- **Adapter** — `start` seeds the cache; the loop writes on interval; `stop` cancels;
  malformed steps are swallowed.
- **Determinism knob** — seed NumPy/`random` in tests for stable assertions.

Run: `cd backend && uv run --extra dev pytest tests/market/ -v`
Live view: `cd backend && uv run market_data_demo.py` (Rich terminal dashboard).
