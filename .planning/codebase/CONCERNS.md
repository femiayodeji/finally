# Codebase Concerns

**Analysis Date:** 2026-07-14

## Overview

The FinAlly codebase is early-stage with one complete subsystem (market data) and substantial unbuilt surface area. This document identifies genuine technical concerns in **existing code** and critical blockers for the platform to run.

**Status Summary:**
- **Complete & Tested:** Market data subsystem (`backend/app/market/`) — 767 LOC, 73 passing tests, 84% coverage
- **Partially Built:** Frontend utilities (contexts, API client, types) — no app structure
- **Unbuilt:** FastAPI app wiring, database layer, portfolio/trade logic, LLM integration, frontend components, Docker

---

## Schema Mismatches & Type Errors

### `session_change_percent` Missing from Backend

**What happens:** Frontend types (`frontend/lib/types.ts:17`) expect a `session_change_percent` field in SSE price updates:
```typescript
export interface PriceUpdate {
  // ... other fields
  session_change_percent: number;  // Line 17
}
```

Backend `PriceUpdate` model (`backend/app/market/models.py`) only provides `change_percent`:
```python
@property
def change_percent(self) -> float:
    """Percentage change from previous update."""
    if self.previous_price == 0:
        return 0.0
    return round((self.price - self.previous_price) / self.previous_price * 100, 4)
```

No `session_change_percent` property or field exists.

**Why it's wrong:** The SSE stream will return `{"ticker": "AAPL", "price": 190.50, "change_percent": 0.52}` but the frontend expects `session_change_percent`. TypeScript will error, and at runtime the field will be `undefined`.

**PLAN.md Context:** §13 (Resolved Design Decision #4) specifies: "the server maintains a bounded in-memory rolling price history (ring buffer) and a session reference price per ticker, computes **change %** server-side". This is specified but not yet implemented in `PriceUpdate`.

**Do this instead:** Add a `session_reference_price` field to the cache initialization and compute `session_change_percent` in `PriceUpdate`:
```python
@property
def session_change_percent(self) -> float:
    """Percentage change from session reference price."""
    if self.session_reference_price == 0:
        return 0.0
    return round((self.price - self.session_reference_price) / self.session_reference_price * 100, 4)
```

**Impact:** **HIGH** — App will crash when SSE delivers prices to the frontend.

---

## Missing Core Infrastructure

### No FastAPI App Entry Point

**Files:** None exist at `backend/app/main.py`, `backend/app/server.py`, or `backend/main.py`

**What's missing:** The market data subsystem is complete with `create_stream_router()` factory, but there's no FastAPI `app = FastAPI()` instance to mount it to. The entry point that uvicorn would run (`uvicorn app.main:app`) doesn't exist.

**Why it matters:** The market data module is dead code without an app. SSE endpoint, portfolio endpoint, trade endpoint, and chat endpoint have no server to run on.

**Do this instead:** Create `backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.market import create_stream_router, create_market_data_source, PriceCache

app = FastAPI()
price_cache = PriceCache()
source = create_market_data_source(price_cache)

# Mount SSE streaming
app.include_router(create_stream_router(price_cache))

# Mount other routers (api.py, etc.) as they're built
# Serve static frontend files
app.mount("/", StaticFiles(directory="static", html=True), name="frontend")

# Lifecycle
@app.on_event("startup")
async def startup():
    await source.start([...default watchlist...])

@app.on_event("shutdown")
async def shutdown():
    await source.stop()
```

**Impact:** **BLOCKING** — Application cannot start.

---

### Empty Database Module

**Files:** `backend/app/db/` directory exists but contains only `__pycache__`

**Missing Implementations:**
- `models.py` — SQLite schema (users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages)
- `init.py` — Database initialization on startup (create tables if missing, seed defaults)
- `queries.py` or similar — CRUD operations for positions, trades, snapshots, chat

**Why it matters:** Per PLAN.md §7, the backend initializes SQLite **on startup, before the market-data task starts**. Without this:
- No persistent portfolio state
- No trade history
- No default watchlist to seed the market-data task
- The market-data task will track an empty ticker set

**Do this instead:** Implement the schema and initialization logic per PLAN.md §7. Seed the default 10 tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) on first run.

**Impact:** **BLOCKING** — Market-data task has no tickers to track; app is non-functional.

---

### Empty API Routes Module

**Files:** `backend/app/api/` directory exists but contains only `__pycache__`

**Missing Endpoints:** All of PLAN.md §8:
- `GET /api/stream/prices` — SSE streaming (partially done: router factory exists but not mounted)
- `GET /api/prices/{ticker}/history` — Price history backfill
- `GET /api/portfolio` — Portfolio state and valuation
- `POST /api/portfolio/trade` — Trade execution
- `GET /api/portfolio/history` — P&L chart data
- `GET /api/watchlist` — Watchlist with prices
- `POST /api/watchlist` — Add ticker
- `DELETE /api/watchlist/{ticker}` — Remove ticker
- `POST /api/chat` — LLM chat with auto-execution
- `GET /api/health` — Health check

**Why it matters:** Frontend calls these endpoints (see `frontend/lib/api.ts`); without them, all data flows fail.

**Do this instead:** Implement each route handler in `backend/app/api/routes.py` or split by domain (e.g., `portfolio.py`, `watchlist.py`, `chat.py`). Mount the APIRouter in `main.py`.

**Impact:** **BLOCKING** — All frontend API calls fail with 404.

---

### Empty Services Module

**Files:** `backend/app/services/` directory exists but contains only `__pycache__`

**Missing Logic:**
- Portfolio valuation (sum of positions + cash balance)
- Trade execution (update positions, cash, record trade, compute average cost)
- P&L calculation (unrealized vs. realized, per-position and total)
- Portfolio snapshots (record every 30s and after trades)

**Why it matters:** Trade endpoint and portfolio endpoint need this logic. The app cannot calculate what a user owns or is worth without it.

**Do this instead:** Create `backend/app/services/portfolio.py` with functions:
```python
async def execute_trade(ticker, side, quantity, current_price, user_id)
async def get_portfolio_state(user_id)  # Includes total_value, positions, P&L
async def record_portfolio_snapshot(user_id)
```

**Impact:** **BLOCKING** — Trading and portfolio viewing are non-functional.

---

### Empty LLM Module

**Files:** `backend/app/llm/` directory exists but contains only `__pycache__`

**Missing Logic:**
- LLM client initialization (LiteLLM + OpenRouter)
- Structured output schema definition for trades + watchlist actions
- Prompt construction (system message, portfolio context, history)
- Response parsing and validation
- Auto-execution of trades with fallback retry logic
- Chat message storage to `chat_messages` table

**Why it matters:** The `/api/chat` endpoint (per PLAN.md §9) is a core feature ("analyze positions and execute trades on the user's behalf"). Without LLM integration, the AI copilot doesn't exist.

**PLAN.md Requirement:** Use LiteLLM + OpenRouter with `openrouter/openai/gpt-oss-120b` and Cerebras inference provider. Structured outputs must be validated before auto-executing trades.

**Do this instead:** Implement per PLAN.md §9. Use the `cerebras-inference` skill for code generation.

**Impact:** **HIGH** — Chat feature is non-functional.

---

## Frontend App Structure Missing

**Files:** No `frontend/package.json`, `frontend/next.config.ts`, `frontend/pages/`, `frontend/app/`, `frontend/components/`, `frontend/tsconfig.json`

**What exists:** Only `frontend/lib/` (contexts, API client, types) and `frontend/out/` (Next.js build output, likely stale).

**Why it matters:** Next.js app cannot build or run without:
- `package.json` (dependencies: Next.js, React, Tailwind, charting library, etc.)
- `next.config.ts` (output: export, rewrites for `/api/*` proxy in dev)
- `tsconfig.json` (TypeScript config)
- `pages/` or `app/` (entry point and route structure)
- Components (watchlist, chart, portfolio heatmap, positions table, trade bar, chat panel)

**Frontend Utilities (Partial):**
- ✅ `frontend/lib/api.ts` — API client functions
- ✅ `frontend/lib/types.ts` — TypeScript types (for SSE, portfolio, watchlist, chat)
- ✅ `frontend/lib/PriceStreamContext.tsx` — SSE connection provider
- ✅ `frontend/lib/WatchlistContext.tsx` — Watchlist state management
- ✅ `frontend/lib/PortfolioContext.tsx` — Portfolio polling
- ❌ `frontend/lib/usePriceHistory.ts` — Likely empty or stub
- ❌ `frontend/lib/format.ts` — Likely empty or stub

**Do this instead:** Create a Next.js project from scratch or use the existing `frontend/` as the source root. Implement:
1. `frontend/package.json` with dependencies
2. `frontend/next.config.ts` for static export + dev proxy
3. `frontend/pages/` or `frontend/app/` with layout and root page
4. Components for each UI section (watchlist, chart, portfolio, etc.)
5. Page to wrap contexts (`PriceStreamProvider`, `WatchlistProvider`, `PortfolioProvider`)

**Impact:** **BLOCKING** — Frontend cannot build.

---

## Secrets Management Risk

**File:** `.env` at repo root

**What's the concern:** The `.env` file contains API keys:
- `OPENROUTER_API_KEY` — LLM integration key
- `MASSIVE_API_KEY` — Real market data key (optional)

**Why it's risky:** If `.env` is committed to git, keys are exposed in the repository history permanently. Even deletion in a later commit leaves the key in older commits accessible via `git log`.

**Verify:** Check if `.env` is in `.gitignore`:
```bash
grep "\.env" /home/femiayodeji/sandbox/andela/augmented-engineering/finally/.gitignore
```

**Do this instead:**
1. Ensure `.gitignore` contains `.env` and `.env.*.local`
2. Commit `.env.example` documenting the structure (no values)
3. Document in README that users must create `.env` with their own keys
4. Use `--env-file` flag in Docker or Docker Compose for production

**Impact:** **MEDIUM** — Potential credential exposure.

---

## Minor Issues & Fragility

### No API Key Validation on Startup

**File:** `backend/app/market/massive_client.py:42`

**What happens:** `MassiveDataSource.__init__` accepts an API key but doesn't validate it. The first error occurs on the first poll attempt (line 89+), not at startup. A bad key silently fails with a logged error, leaving the user confused.

**Do this instead:** Call the Massive API in `start()` to validate the key before returning:
```python
async def start(self, tickers: list[str]) -> None:
    try:
        await self._validate_key()
    except Exception as e:
        logger.error("Invalid Massive API key: %s", e)
        raise
```

**Impact:** **LOW** — Affects Massive mode only, caught quickly in logs.

---

### Random Shock Events Undocumented to User

**File:** `backend/app/market/simulator.py:105-108`

**What happens:** The GBM simulator includes random price shocks (0.1% chance per tick, 2-5% magnitude) without user knowledge. Unexpected large moves may confuse demo users.

**Logging:** Events are logged at `DEBUG` level (line 109), not `INFO`, so they're hidden by default.

**Do this instead:** Document in PLAN.md and log at `INFO` level, or make shock probability a configurable parameter with a default of 0.0 for demos.

**Impact:** **LOW** — Demo feature, works as designed but undiscovered.

---

### SSE Stream Has No Event Type Discrimination

**File:** `backend/app/market/stream.py:81-83`

**What happens:** SSE sends only `data: {...}` with no `event: type` field. If multiple event types are needed later (e.g., price updates vs. connection status), the format must change.

**Do this instead:** Add an event type field for future extensibility:
```python
data = {
    "type": "prices",  # Future: could be "status", "error", etc.
    "payload": {ticker: update.to_dict() for ticker, update in prices.items()}
}
yield f"data: {json.dumps(data)}\n\n"
```

**Impact:** **LOW** — Forward-compatibility concern, not a current bug.

---

### Price History Lost on Restart

**File:** `backend/app/market/cache.py` — in-memory only

**What happens:** Per PLAN.md §6, price history is stored in-memory only (not persisted to SQLite). Every restart clears the rolling buffer. Charts backfill from this buffer on load; after restart, they start empty and populate live.

**Is this correct?** Yes, per PLAN.md: "per-tick DB writes would be wasteful and hurt latency; durable time-series persistence is reserved for `portfolio_snapshots`."

**Awareness:** This is a documented design choice, not a bug. But it should be tested: verify that charts gracefully show empty history on cold start and populate as prices stream in.

**Impact:** **LOW** — Expected behavior.

---

### Polling Interval Race in Massive Client

**File:** `backend/app/market/massive_client.py:41-51`

**What happens:** `start()` does an immediate poll (line 46) to seed the cache. The background task starts (line 48). Between these lines, if `remove_ticker()` is called, there's no guarantee the removed ticker won't be polled anyway. The removed ticker won't be in `self._tickers` but might appear in the poll result if the timing aligns.

**Real risk?** Very low — the window is milliseconds and the code handles unexpected tickers gracefully (line 100-115). But it's a minor race.

**Do this instead:** Lock or flag the polling state, or queue remove requests until after the first poll completes.

**Impact:** **VERY LOW** — Unlikely in practice, gracefully handled.

---

## Test Coverage Gaps

### Database Module Untested

**Status:** No tests exist for database initialization, schema creation, or CRUD operations.

**Why:** The database module doesn't exist yet.

**Plan:** Once the module is built, add tests for:
- Schema creation (tables exist after init)
- Seeding (default watchlist populates)
- Trade execution (position updates, cash balance changes, trades logged)
- Portfolio snapshot recording

**Impact:** **MEDIUM** — Core logic, must be tested before deployment.

---

### API Routes Untested

**Status:** No tests exist for the API endpoints (they don't exist yet).

**Why:** The API module doesn't exist yet.

**Plan:** Add tests for:
- `/api/portfolio` — returns correct total_value, positions, P&L
- `/api/portfolio/trade` — buys/sells work, validation rejects insufficient funds/shares
- `/api/watchlist` — add/remove/list work, duplicates handled
- `/api/chat` — structured output is parsed, trades are auto-executed
- `/api/stream/prices` — SSE delivers valid price frames

**Impact:** **HIGH** — Core feature, must be tested.

---

### LLM Integration Untested

**Status:** No tests exist for LLM chat, structured output parsing, or auto-execution.

**Why:** The LLM module doesn't exist yet.

**Plan:** Add tests for:
- Structured output validation (malformed JSON rejected, schema enforced)
- Trade auto-execution (valid trades execute, invalid trades fail gracefully)
- Watchlist changes (add/remove through chat)
- Fallback on malformed output (retry once, return error)

**Impact:** **HIGH** — Agentic feature, must be tested.

---

## Frontend Component Tests Missing

**Status:** No unit tests for React components (components don't exist yet).

**Why:** Component library not built.

**Plan:** Add tests for:
- Price flash animation (green/red highlight on direction change)
- Watchlist rendering (tickers, prices, sparklines)
- Portfolio heatmap (sizes and colors reflect P&L)
- P&L chart (line chart renders, updates on SSE price stream)
- Chat panel (messages, loading state, action confirmations)
- Trade bar (buy/sell buttons, quantity input validation)

**Impact:** **MEDIUM** — Frontend quality depends on this.

---

## Summary Table

| Concern | Severity | Category | Blocker? |
|---------|----------|----------|----------|
| `session_change_percent` schema mismatch | HIGH | Type Error | YES |
| No FastAPI app entry point | HIGH | Infrastructure | YES |
| Empty database module | HIGH | Infrastructure | YES |
| Empty API routes module | HIGH | Infrastructure | YES |
| Empty services module (portfolio/trade logic) | HIGH | Infrastructure | YES |
| Empty LLM module | HIGH | Feature | YES |
| Frontend app structure missing | HIGH | Infrastructure | YES |
| Secrets management (`.env` in repo risk) | MEDIUM | Security | |
| No API key validation in Massive | LOW | Error Handling | |
| Random shock events undocumented | LOW | UX | |
| SSE stream has no event type field | LOW | Forward Compatibility | |
| Price history lost on restart | LOW | Expected Limitation | |
| Polling interval race in Massive | VERY LOW | Edge Case | |
| Database module untested | MEDIUM | Testing Gap | |
| API routes untested | HIGH | Testing Gap | |
| LLM integration untested | HIGH | Testing Gap | |
| Frontend component tests missing | MEDIUM | Testing Gap | |

---

*Concerns audit: 2026-07-14*
