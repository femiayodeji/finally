# Massive API Reference (formerly Polygon.io)

Reference for the **Massive** market-data REST API as used by FinAlly's real-data path.
Massive is the rebrand of Polygon.io; the REST surface and the Python client are
API-compatible with Polygon's, so existing Polygon knowledge and tooling apply directly.

FinAlly uses this API **only when `MASSIVE_API_KEY` is set**. Otherwise it runs the
built-in simulator (see `MARKET_SIMULATOR.md`). Both sit behind one interface
(see `MARKET_INTERFACE.md`), so nothing downstream of the price cache knows or cares
which source is live.

> **Scope for FinAlly.** We need exactly one thing from this API in the hot path:
> the **latest price for a set of tickers, fetched in a single request**, polled on a
> timer. Everything else here (previous close, historical bars) is documented for
> completeness and for optional chart backfill, but is not required for the core loop.

---

## 1. Basics

| | |
|---|---|
| **Base URL** | `https://api.massive.com` (Polygon's `https://api.polygon.io` remains compatible) |
| **Python package** | `massive` — `uv add massive` (already a backend dependency) |
| **Min Python** | 3.9+ |
| **Auth** | API key, sent as `Authorization: Bearer <KEY>`. The client adds this automatically. |
| **Key source** | `MASSIVE_API_KEY` env var (read from project-root `.env`) |
| **Timestamps** | Unix **milliseconds** in every REST payload — divide by 1000 for seconds |
| **Ticker case** | Tickers are **case-sensitive**; always send uppercase |

### Client initialization

```python
from massive import RESTClient

# Explicit key (what FinAlly does — the key is already loaded from .env):
client = RESTClient(api_key=api_key)

# Or, if MASSIVE_API_KEY is exported into the environment, no arg is needed:
client = RESTClient()
```

The `RESTClient` is **synchronous** (blocking HTTP under the hood). FinAlly runs it
inside `asyncio.to_thread(...)` so it never blocks the event loop — see §6.

---

## 2. Rate limits & polling cadence

| Tier | Request budget | FinAlly poll interval |
|------|----------------|-----------------------|
| Free / Basic | 5 requests / minute | **15 s** (default) |
| Starter / Developer | Higher, effectively unlimited for our use | 2–5 s |
| Advanced / Business | Real-time, high throughput | 2 s |

The single most important consequence for the design: **one snapshot call returns
every ticker we care about**, so our per-cycle cost is *one* request regardless of
watchlist size. A 10-ticker watchlist polled every 15 s uses 4 req/min — inside the
free-tier budget with headroom. This is why we poll the *snapshot* endpoint and never
loop per-ticker.

Data freshness also depends on tier: free/starter data may be **15-minute delayed**;
real-time requires a paid real-time plan. FinAlly treats whatever price it receives as
current — delayed data is fine for a simulated portfolio.

---

## 3. Primary endpoint — Full Market Snapshot (multiple tickers, one call)

This is the endpoint FinAlly polls. It returns the latest daily bar, minute bar,
previous-day bar, last trade, and last quote for each requested ticker in a **single
response**.

**REST**
```
GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT
```

Query parameters:

| Param | Type | Notes |
|-------|------|-------|
| `tickers` | comma-separated list | Case-sensitive. Omit / empty string ⇒ **all** ~10,000 tickers (do not do this — always pass our set). |
| `include_otc` | boolean | Include OTC securities. Default `false`. Leave off. |

**Python client**

```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient(api_key=api_key)

snapshots = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,
    tickers=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
)

for snap in snapshots:
    print(f"{snap.ticker}: ${snap.last_trade.price}  "
          f"({snap.todays_change_percent:+.2f}% today)")
```

### Response shape

Top level: `{ "status": ..., "count": N, "tickers": [ <snapshot>, ... ] }`.
The Python client unwraps this and yields the per-ticker snapshot objects directly.

Each snapshot (raw JSON keys ⇒ Python client attribute):

```json
{
  "ticker": "AAPL",
  "todaysChange": -4.54,
  "todaysChangePerc": -3.50,
  "updated": 1675190399000,
  "day":      { "o": 129.61, "h": 130.15, "l": 125.07, "c": 125.07, "v": 111237700, "vw": 127.35 },
  "prevDay":  { "o": 128.00, "h": 129.95, "l": 127.10, "c": 129.61, "v": 90000000,  "vw": 128.50 },
  "min":      { "o": 125.10, "h": 125.20, "l": 125.00, "c": 125.07, "v": 12000, "vw": 125.09, "t": 1675190340000, "av": 111200000, "n": 42 },
  "lastTrade":{ "p": 125.07, "s": 100, "t": 1675190399000, "x": 11, "c": [37], "i": "12345" },
  "lastQuote":{ "P": 125.08, "S": 10, "p": 125.06, "s": 5, "t": 1675190399500 }
}
```

**Raw key → Python attribute → meaning** (the fields FinAlly reads are in **bold**):

| Raw JSON | Client attribute | Meaning |
|----------|------------------|---------|
| `ticker` | **`snap.ticker`** | Symbol |
| `todaysChange` | `snap.todays_change` | Absolute change vs prev close |
| `todaysChangePerc` | `snap.todays_change_percent` | % change vs prev close (session-day change) |
| `updated` | `snap.updated` | Last-update ns/ms timestamp |
| `day.c` | `snap.day.close` | Latest daily close (0 pre-market) |
| `day.o/h/l/v/vw` | `snap.day.open/high/low/volume/vwap` | Daily OHLCV |
| `prevDay.c` | `snap.prev_day.close` | **Previous session close** (reference for day change) |
| `lastTrade.p` | **`snap.last_trade.price`** | **Most recent trade price ← FinAlly's live price** |
| `lastTrade.s` | `snap.last_trade.size` | Trade size |
| `lastTrade.t` | **`snap.last_trade.timestamp`** | **Trade time (ms) ← FinAlly's price timestamp** |
| `lastQuote.p` / `.P` | `snap.last_quote.bid_price` / `.ask_price` | NBBO bid / ask |

> **Field-name caution.** The **day-change percentage lives at the top level**
> (`todays_change_percent`), *not* inside `day`. The **previous close** is
> `prev_day.close`, *not* `day.previous_close`. (Earlier drafts of this doc got this
> wrong.) FinAlly does not depend on either for its own change % — it computes change %
> server-side against a session-reference price (see `MARKET_INTERFACE.md` §"Change %").

### What FinAlly extracts

Only three fields per snapshot:

```python
price     = snap.last_trade.price          # → PriceCache
timestamp = snap.last_trade.timestamp / 1000.0   # ms → seconds
ticker    = snap.ticker
```

Robustness matters here: during pre-market/holidays or for a thinly traded symbol,
`last_trade` can be `None` or missing. FinAlly guards each snapshot in a
`try/except (AttributeError, TypeError)` and skips malformed entries rather than
crashing the poll cycle (see §6).

---

## 4. Secondary endpoints (not in the hot path)

### 4a. Single-Ticker Snapshot
Same data as above for one symbol — useful for a detail view.

```
GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}
```
```python
snap = client.get_snapshot_ticker(
    market_type=SnapshotMarketType.STOCKS,
    ticker="AAPL",
)
print(snap.last_trade.price, snap.prev_day.close)
```

### 4b. Unified Snapshot (v3, cross-asset)
Newer endpoint; returns a normalized `session` object with clean field names and
supports up to 250 tickers via `ticker.any_of`.

```
GET /v3/snapshot?ticker.any_of=AAPL,GOOGL,MSFT&type=stocks
```
Response `results[]` items carry `ticker`, `type`, `name`, `market_status`, and a
`session` object with `price`, `change`, `change_percent`, `open/high/low/close`,
`previous_close`, `volume`, plus `last_trade` / `last_quote`. Unfound tickers come back
as error objects in the same array (so a bad symbol doesn't fail the whole request).
FinAlly uses the v2 full-market snapshot (§3) for parity with the existing client
methods, but v3 is a clean upgrade path if we ever want per-symbol error reporting.

### 4c. Previous Close (for seed prices / validation)
```
GET /v2/aggs/ticker/{ticker}/prev
```
```python
prev = client.get_previous_close_agg(ticker="AAPL")
for agg in prev:                       # single-element iterable
    print(agg.close, agg.open, agg.high, agg.low, agg.volume)
```
Results carry `o,h,l,c,v,vw,t,n`. Useful to (a) seed a realistic opening price for a
newly added ticker and (b) **validate** that a symbol resolves to real data before
accepting it onto the watchlist in Massive mode (PLAN §8).

### 4d. Custom Aggregate Bars (optional historical charts)
```
GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}
```
```python
bars = list(client.list_aggs(
    ticker="AAPL", multiplier=1, timespan="minute",
    from_="2024-01-02", to="2024-01-02", limit=50000,
))
for b in bars:
    print(b.timestamp, b.open, b.high, b.low, b.close, b.volume)
```
Path params: `multiplier` (int), `timespan` (`minute|hour|day|week|month|...`),
`from`/`to` (`YYYY-MM-DD` or epoch-ms). Query: `adjusted` (default true),
`sort` (`asc|desc`), `limit` (max 50000). Not used by the live loop — FinAlly's charts
backfill from the in-memory rolling history, not from Massive (PLAN §6).

---

## 5. Error handling

The client raises on HTTP errors. The poller must swallow these and retry on the next
tick — a transient failure should never kill the background task.

| Status | Cause | FinAlly response |
|--------|-------|------------------|
| `401` | Invalid / missing API key | Log; keep looping (prices go stale, app stays up) |
| `403` | Plan doesn't cover the endpoint | Log; keep looping |
| `429` | Rate limit exceeded | Log; the fixed poll interval already paces us; next tick retries |
| `5xx` | Massive server error | Client retries a few times internally; otherwise next tick |
| network / timeout | Connectivity | Log; next tick retries |

The rule: **one broad `except Exception` around the fetch+parse, log, and return** —
never re-raise out of the loop body.

---

## 6. Reference: the polling pattern FinAlly uses

This mirrors `backend/app/market/massive_client.py`. The synchronous client call is
offloaded with `asyncio.to_thread`; parsing is defensive; failures are contained.

```python
import asyncio, logging
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

logger = logging.getLogger(__name__)

class MassivePoller:
    def __init__(self, api_key, cache, tickers, interval=15.0):
        self._client = RESTClient(api_key=api_key)
        self._cache = cache
        self._tickers = list(tickers)
        self._interval = interval

    async def poll_once(self):
        if not self._tickers:
            return
        try:
            # Blocking client → run off the event loop
            snapshots = await asyncio.to_thread(
                self._client.get_snapshot_all,
                SnapshotMarketType.STOCKS,
                self._tickers,
            )
            for snap in snapshots:
                try:
                    self._cache.update(
                        ticker=snap.ticker,
                        price=snap.last_trade.price,
                        timestamp=snap.last_trade.timestamp / 1000.0,  # ms → s
                    )
                except (AttributeError, TypeError) as e:
                    logger.warning("skip %s: %s", getattr(snap, "ticker", "?"), e)
        except Exception as e:
            logger.error("Massive poll failed: %s", e)   # never re-raise

    async def run(self):
        await self.poll_once()                 # immediate first fill
        while True:
            await asyncio.sleep(self._interval)
            await self.poll_once()
```

Notes that matter:

- **Immediate first poll** in `run()` before the sleep, so the cache is populated the
  instant the app starts rather than after one interval.
- **One request per cycle** — `get_snapshot_all` covers the whole tracked set.
- The tracked set is **watchlist ∪ open positions** (PLAN §6); the poller is handed
  that union, not the raw watchlist.
- Only `last_trade.price` and `last_trade.timestamp` are consumed; everything else in
  the snapshot is ignored. Change %, valuation, and history are computed by the cache
  layer, not read from Massive (PLAN §3, "backend owns the core").

---

## 7. Sources

- [Massive — Full Market Snapshot](https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot)
- [Massive — Single Ticker Snapshot](https://massive.com/docs/rest/stocks/snapshots/single-ticker-snapshot)
- [Massive — Unified Snapshot (v3)](https://massive.com/docs/rest/stocks/snapshots/unified-snapshot)
- [Massive — Custom Aggregate Bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
- [Massive — Stocks REST overview](https://massive.com/docs/rest/stocks/overview)
- Python client method names verified against `backend/app/market/massive_client.py`
  (Polygon-compatible `massive` package).
