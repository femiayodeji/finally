<!-- refreshed: 2026-07-14 -->
# Architecture

**Analysis Date:** 2026-07-14

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js Export)                │
│          `frontend/lib/` + pages/components (TBD)            │
│                                                              │
│  PriceStreamContext | PortfolioContext | WatchlistContext   │
│         (SSE)       |   (4s polling)    |   (on-demand)      │
└────────┬─────────────────────┬─────────────────────┬────────┘
         │                     │                     │
         ▼ SSE                 ▼ REST polling        ▼ REST
      /api/stream/prices  /api/portfolio        /api/watchlist
      /api/prices/:ticker  /api/portfolio/       /api/chat
                           history               (implemented)
                           /api/portfolio/trade  (scaffolded)
                           /api/chat
                           (all scaffolded)
│
│
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (TBD)                      │
│               Entry point and request routing                │
│                  `app/main.py` (missing)                     │
├──────────────────┬──────────────────┬───────────────────────┤
│    Market Data   │   Portfolio      │  Chat & LLM          │
│   (IMPLEMENTED)  │  (scaffolded)    │  (scaffolded)         │
│ `app/market/`    │ `app/services/`  │ `app/llm/`            │
│                  │ `app/api/`       │ `app/services/`       │
├──────────────────┼──────────────────┼───────────────────────┤
│  - PriceCache    │ - Trade exec     │ - LLM client          │
│  - GBM Simulator │ - P&L calc       │ - Structured output   │
│  - Massive API   │ - Watchlist CRUD │ - Trade validation    │
│  - SSE stream    │                  │ - Chat history        │
└──────────────────┴──────────────────┴───────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                  SQLite Database (TBD)                       │
│               `db/finally.db` (volume-mounted)               │
│                                                              │
│  - users_profile  - trades        - chat_messages           │
│  - watchlist      - positions     - portfolio_snapshots     │
│  (schema/seed in `app/db/` — scaffolded)                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File(s) | Status |
|-----------|----------------|---------|--------|
| **PriceCache** | Thread-safe in-memory price store with version counter | `app/market/cache.py` | ✅ Implemented |
| **PriceUpdate** | Immutable dataclass: ticker, price, previous_price, timestamp, change %, direction | `app/market/models.py` | ✅ Implemented |
| **MarketDataSource** | Abstract interface for price providers (Simulator or Massive) | `app/market/interface.py` | ✅ Implemented |
| **SimulatorDataSource** | GBM-based market simulator with correlated tickers | `app/market/simulator.py` | ✅ Implemented |
| **MassiveDataSource** | REST polling client for Polygon.io (via Massive SDK) | `app/market/massive_client.py` | ✅ Implemented |
| **SSE Stream Router** | FastAPI router: `GET /api/stream/prices` — pushes price updates every 500ms | `app/market/stream.py` | ✅ Implemented |
| **FastAPI App** | Main entrypoint, route registration, middleware, DB init, market data startup | `app/main.py` (missing) | ⬜ Scaffolded |
| **API Routes** | REST endpoints: `/api/portfolio`, `/api/watchlist`, `/api/chat`, `/api/prices`, `/api/health` | `app/api/` (empty) | ⬜ Scaffolded |
| **DB Layer** | SQLite schema, initialization, CRUD operations, migrations | `app/db/` (empty) | ⬜ Scaffolded |
| **Portfolio Service** | Trade execution, P&L calculation, position management, cash balance | `app/services/portfolio_service.py` (missing) | ⬜ Scaffolded |
| **Watchlist Service** | Ticker validation, add/remove, sync with market data tracking | `app/services/watchlist_service.py` (missing) | ⬜ Scaffolded |
| **LLM Service** | Chat message handling, structured output parsing, auto-execution | `app/llm/service.py` (missing) | ⬜ Scaffolded |
| **LLM Client** | LiteLLM → OpenRouter integration, Cerebras inference | `app/llm/client.py` (missing) | ⬜ Scaffolded |
| **Frontend Data Contexts** | React contexts for SSE, portfolio polling, watchlist CRUD | `frontend/lib/{PriceStream,Portfolio,Watchlist}Context.tsx` | ✅ Implemented |
| **Frontend API Client** | Type-safe fetch wrapper for all `/api/*` endpoints | `frontend/lib/api.ts` | ✅ Implemented |
| **Frontend Types** | TypeScript definitions for all API requests/responses | `frontend/lib/types.ts` | ✅ Implemented |

## Pattern Overview

**Overall:** Backend-owns-core, thin frontend rendering layer

**Key Characteristics:**
- **Backend computes all core numbers** — valuation, P&L, change %, price history; frontend only displays
- **SSE for live prices**, REST polling for slower-changing portfolio state
- **Market data is the seam** — in-memory cache (`PriceCache`) designed to move to Redis for multi-user scaling without changing downstream code
- **Layered separation** — market data (input), services (logic), API (output)
- **No global state** — dependency injection via factory functions and context providers

## Layers

**Market Data Layer:**
- Purpose: Acquire, cache, and stream live price data
- Location: `app/market/`
- Contains: Data sources (simulator + Massive API), price cache, SSE streaming router
- Depends on: Python stdlib, numpy (for GBM), massive SDK (optional), FastAPI
- Used by: SSE endpoint, portfolio service (price lookups), API routes

**Service Layer:**
- Purpose: Business logic — trades, portfolio valuation, watchlist management, LLM interaction
- Location: `app/services/` + `app/llm/`
- Contains: Trade execution, P&L math, watchlist CRUD, chat flow, LLM calls
- Depends on: Market data (price cache), database, LLM client
- Used by: API routes

**API Layer:**
- Purpose: HTTP endpoints, request/response handling, validation
- Location: `app/api/`
- Contains: Routes for portfolio, watchlist, chat, prices, health check
- Depends on: Services, market data
- Used by: Frontend, external clients

**Database Layer:**
- Purpose: Persistence — user profiles, positions, trades, chat history, snapshots
- Location: `app/db/`
- Contains: Schema definitions, initialization, CRUD helpers per table
- Depends on: SQLite
- Used by: Services

**Frontend Data Layer:**
- Purpose: Real-time subscription and state management
- Location: `frontend/lib/`
- Contains: React contexts for price stream (SSE), portfolio polling, watchlist CRUD; API client
- Depends on: Browser APIs (EventSource, fetch)
- Used by: Page components (TBD)

## Data Flow

### Primary Request Path: Trade Execution

1. **Frontend** — User clicks "Buy 10 AAPL" → calls `executeTrade("AAPL", "buy", 10)` (`frontend/lib/api.ts:51`)
2. **HTTP POST** → `POST /api/portfolio/trade` with body `{ticker, side, quantity}` (currently unimplemented)
3. **API Route** → Parses request, calls `portfolio_service.execute_trade(...)` (location TBD, `app/api/portfolio.py`)
4. **Portfolio Service** → Validates (sufficient cash for buy, sufficient shares for sell); reads current price from `PriceCache.get_price()` (`app/market/cache.py:54`); updates position (recomputes avg_cost on buy, deletes row on sell); decrements cash; writes trade to SQLite `trades` table (location TBD, `app/db/trades.py`)
5. **Snapshot** → Writes row to `portfolio_snapshots` table immediately after trade (location TBD, `app/db/snapshots.py`)
6. **Response** → Returns updated `Portfolio` object: cash_balance, positions_value (from prices + quantities), total_value, positions[]
7. **Frontend** → Receives response, updates `PortfolioContext`, triggers re-render of header (total value), positions table, heatmap

### Secondary Flow: SSE Price Stream

1. **Market Data Task** — Simulator or Massive poller updates `PriceCache.update("AAPL", 190.50)` every 500ms (`app/market/cache.py:23`)
   - Automatically computes change, change_percent, direction vs. previous_price
   - Increments cache version counter on each update
2. **SSE Generator** — `_generate_events()` reads cache version; if changed, serializes all prices to JSON and yields SSE event (`app/market/stream.py:51`)
3. **Browser** — `EventSource` receives event, parses JSON frame: `{"AAPL": {price, change_percent, direction, ...}, "GOOGL": {...}}`
4. **Frontend** — `PriceStreamProvider` updates `PriceStreamContext.prices`, all consumers re-render:
   - Watchlist rows update price and apply color flash CSS
   - Main chart extends data series
   - Header updates individual tickers

### Tertiary Flow: Portfolio Polling

1. **Frontend Mount** — `PortfolioProvider` calls `getPortfolio()` immediately, then every 4 seconds (`frontend/lib/PortfolioContext.tsx:50`)
2. **HTTP GET** → `GET /api/portfolio` (currently unimplemented)
3. **API Route** → Queries current user's positions, cash, and latest prices from `PriceCache`; computes total_value (cash + sum of position market values); computes unrealized P&L per position (location TBD, `app/api/portfolio.py`)
4. **Response** → JSON: `{cash_balance, positions_value, total_value, total_unrealized_pnl, positions: [{ticker, quantity, avg_cost, current_price, market_value, unrealized_pnl, unrealized_pnl_percent}]}`
5. **Frontend** → `PortfolioContext` stores portfolio, triggers re-renders of header, positions table, heatmap

**State Management:**
- **Prices**: Real-time source of truth in `PriceCache`; distributed via SSE to frontend; frontend does NOT poll REST for live updates
- **Portfolio**: Periodic REST polling every 4s; computed server-side (never client-side); updates trigger UI re-renders
- **Watchlist**: Loaded on mount + on-demand add/remove; initial paint includes price snapshot from cache
- **Chat**: Stateless per request; conversation history stored in SQLite; on response, trades are auto-executed and watchlist changes applied

## Key Abstractions

**PriceUpdate:**
- Purpose: Immutable snapshot of a single ticker's state at a point in time
- Examples: `app/market/models.py:10`
- Pattern: Dataclass with computed properties (change, change_percent, direction); `to_dict()` for JSON serialization
- Used by: Cache, SSE stream, API responses, frontend types

**MarketDataSource:**
- Purpose: Abstract interface for pluggable price sources
- Examples: `app/market/interface.py`
- Pattern: Abstract base class (ABC); implementations: `SimulatorDataSource`, `MassiveDataSource`; factory selects based on `MASSIVE_API_KEY` env var
- Used by: FastAPI app startup, price updates

**PriceCache:**
- Purpose: Single source of truth for live prices; thread-safe; version counter for SSE change detection
- Examples: `app/market/cache.py`
- Pattern: Lock-protected dict; `update()` returns `PriceUpdate`; version increments on every write
- Used by: SSE stream, portfolio service (price lookups), API routes (watchlist validation)

**Portfolio (TypeScript Interface):**
- Purpose: Complete snapshot of user's financial state
- Examples: `frontend/lib/types.ts:58`
- Pattern: Immutable data structure (computed server-side); includes aggregates (total_value, total_unrealized_pnl) and details (positions array)
- Used by: PortfolioContext, header, positions table, heatmap

## Entry Points

**FastAPI App** (TBD, location: `app/main.py`):
- Location: Missing (to be implemented)
- Triggers: `uvicorn app.main:app` at container startup (Dockerfile CMD)
- Responsibilities:
  - Create FastAPI app instance
  - Register routers: `/api/stream/*`, `/api/portfolio`, `/api/watchlist`, `/api/chat`, `/api/prices`, `/api/health`
  - Initialize SQLite database (run schema + seed on first startup)
  - Start market data background task (`await market_source.start(watchlist_tickers)`)
  - Serve static frontend files from `static/` directory

**Market Data Simulator** (for demo):
- Location: `backend/market_data_demo.py`
- Triggers: `uv run market_data_demo.py`
- Responsibilities: Displays live terminal dashboard of simulated prices; demonstrates market data subsystem in isolation

**Frontend App** (TBD, pages/components not yet created):
- Location: `frontend/` (index page/root layout to be implemented)
- Triggers: Browser navigation to `http://localhost:8000` after backend starts
- Responsibilities:
  - Provide root layout with providers: `PriceStreamProvider`, `PortfolioProvider`, `WatchlistProvider`
  - Render main page components: watchlist, chart, portfolio, positions, heatmap, chat

## Architectural Constraints

- **Threading:** Market data source runs one background task (simulator or Massive poller). SSE streaming is async and can handle multiple concurrent clients. Database writes are serialized (SQLite default). No worker threads, no multiprocessing.
- **Global state:** `PriceCache` instance is created once at app startup, passed to market data source and SSE router via dependency injection (no module-level singletons). FastAPI dependency injection for database connection.
- **Circular imports:** None expected. Market data layer has no dependency on services/API; services depend on market data (one-way).
- **In-memory state:** `PriceCache` holds only latest price + previous price per ticker + bounded rolling history (TBD). Full time-series persistence lives in `portfolio_snapshots` table (append-only, 30s intervals + post-trade). Price cache resets on restart; chart backfills from `GET /api/prices/{ticker}/history`.
- **Single-user:** All database records default `user_id="default"`. API does not check auth; ready for multi-user scaling but not implemented.
- **No bidirectional channels:** SSE is one-way (server → client); WebSocket not used. Simpler, universal browser support.
- **Static build frontend:** Next.js exports to static HTML/CSS/JS; FastAPI serves it alongside API routes. No SSR needed.

## Anti-Patterns

### Avoided: Client-Side Computation of Core Numbers

**What would happen:** Frontend reads SSE prices and computes portfolio valuation, P&L, change % on the fly.

**Why it's wrong:** Every browser tab re-computes independently, sees different numbers. Reloading the page loses all state. Clients could cheat by computing false P&L. Scaling to multi-user becomes impossible without a shared authoritative source.

**Do this instead:** Server computes all numbers, stores in database (snapshots) and in-memory cache (for SSE), exposes via REST polling. Frontend is a dumb display layer (`frontend/lib/PortfolioContext.tsx:23`).

### Avoided: Polling REST for Live Price Updates

**What would happen:** Frontend `setInterval()` calls `GET /api/portfolio` (which includes latest price) to "update" the header price.

**Why it's wrong:** Stale prices on each poll cycle. Multiple polling loops (one per ticker, or one per client) create load. No natural synchronization across browsers or tabs. Race conditions on trade execution (client reads stale price, submits trade, filled at different price).

**Do this instead:** SSE stream is the source of truth for live prices. REST polling (4s for portfolio) is for slower-changing aggregate data. (`frontend/lib/PriceStreamContext.tsx:35` and `frontend/lib/PortfolioContext.tsx:50`).

### Avoided: Storing Realized P&L Separately

**What would happen:** Track "profit from closed trades" and "profit from open trades" in separate columns; compute account performance from realized + unrealized.

**Why it's wrong:** Adds complexity to close and re-open the same position; fragile if a trade is partially filled. Historical P&L is harder to report (need to replay realized gains across time).

**Do this instead:** Track only unrealized P&L (via `avg_cost`); performance is "current total portfolio value vs. historical snapshots". (`planning/PLAN.md` §7).

---

*Architecture analysis: 2026-07-14*
