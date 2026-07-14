# Codebase Structure

**Analysis Date:** 2026-07-14

## Directory Layout

```
finally/
├── backend/                          # Python/FastAPI backend (uv project)
│   ├── app/
│   │   ├── __init__.py               # (empty)
│   │   ├── main.py                   # (MISSING) FastAPI app, route registration, startup
│   │   ├── market/                   # ✅ IMPLEMENTED: Price data subsystem
│   │   │   ├── __init__.py           # Public API exports
│   │   │   ├── interface.py          # MarketDataSource abstract base
│   │   │   ├── models.py             # PriceUpdate dataclass
│   │   │   ├── cache.py              # PriceCache (thread-safe in-memory)
│   │   │   ├── simulator.py          # GBM-based SimulatorDataSource
│   │   │   ├── massive_client.py     # REST polling MassiveDataSource
│   │   │   ├── factory.py            # create_market_data_source()
│   │   │   ├── stream.py             # create_stream_router() — SSE endpoint
│   │   │   └── seed_prices.py        # Default tickers, correlation groups, params
│   │   ├── api/                      # ⬜ SCAFFOLDED: REST endpoint routers
│   │   │   ├── __init__.py           # (missing)
│   │   │   ├── portfolio.py          # (missing) GET/POST /api/portfolio*, /api/prices
│   │   │   ├── watchlist.py          # (missing) GET/POST/DELETE /api/watchlist*
│   │   │   ├── chat.py               # (missing) POST /api/chat
│   │   │   └── health.py             # (missing) GET /api/health
│   │   ├── services/                 # ⬜ SCAFFOLDED: Business logic
│   │   │   ├── __init__.py           # (missing)
│   │   │   ├── portfolio_service.py  # (missing) Trade exec, P&L, position mgmt
│   │   │   ├── watchlist_service.py  # (missing) Add/remove tickers, sync tracking
│   │   │   └── errors.py             # (missing) Custom exceptions
│   │   ├── db/                       # ⬜ SCAFFOLDED: Database layer
│   │   │   ├── __init__.py           # (missing)
│   │   │   ├── connection.py         # (missing) SQLite connection setup
│   │   │   ├── init_db.py            # (missing) Schema creation + seed data
│   │   │   ├── users.py              # (missing) CRUD: users_profile
│   │   │   ├── watchlist.py          # (missing) CRUD: watchlist
│   │   │   ├── positions.py          # (missing) CRUD: positions
│   │   │   ├── trades.py             # (missing) CRUD: trades (append-only)
│   │   │   ├── snapshots.py          # (missing) CRUD: portfolio_snapshots
│   │   │   ├── chat.py               # (missing) CRUD: chat_messages
│   │   │   └── util.py               # (missing) Helpers (uuids, timestamps, etc.)
│   │   └── llm/                      # ⬜ SCAFFOLDED: LLM integration
│   │       ├── __init__.py           # (missing)
│   │       ├── client.py             # (missing) LiteLLM → OpenRouter interface
│   │       ├── schema.py             # (missing) Pydantic models for structured output
│   │       └── service.py            # (missing) Chat flow, auto-execution
│   ├── static/                       # Frontend build output (mounted here by Docker)
│   │   └── _next/                    # (next.js build artifacts)
│   ├── tests/
│   │   ├── conftest.py               # pytest fixtures (empty)
│   │   ├── market/                   # ✅ Market data tests
│   │   │   ├── test_models.py        # PriceUpdate properties
│   │   │   ├── test_cache.py         # PriceCache operations
│   │   │   ├── test_simulator.py     # GBM math, correlation, add/remove tickers
│   │   │   ├── test_simulator_source.py  # SimulatorDataSource async lifecycle
│   │   │   ├── test_massive.py       # MassiveDataSource (mocked API responses)
│   │   │   └── test_factory.py       # create_market_data_source logic
│   │   ├── api/                      # ⬜ SCAFFOLDED: Route tests (TBD)
│   │   ├── db/                       # ⬜ SCAFFOLDED: Database tests (TBD)
│   │   ├── services/                 # ⬜ SCAFFOLDED: Service logic tests (TBD)
│   │   └── llm/                      # ⬜ SCAFFOLDED: LLM integration tests (TBD)
│   ├── market_data_demo.py           # ✅ Standalone demo: terminal dashboard
│   ├── pyproject.toml                # uv project config: deps, scripts, pytest/ruff/coverage config
│   ├── uv.lock                       # Dependency lockfile (reproducible builds)
│   ├── CLAUDE.md                     # Backend developer guide (market data API)
│   └── README.md                     # Setup instructions
│
├── frontend/                         # Next.js TypeScript project
│   ├── lib/                          # ✅ IMPLEMENTED: Data layer & utilities
│   │   ├── types.ts                  # TypeScript types (mirrors PLAN.md §8)
│   │   ├── api.ts                    # Fetch client: all `/api/*` endpoints
│   │   ├── format.ts                 # Currency, percentage formatting
│   │   ├── usePriceHistory.ts        # Hook: fetch + cache price history
│   │   ├── PriceStreamContext.tsx    # ✅ React context: SSE prices (EventSource)
│   │   ├── PortfolioContext.tsx      # ✅ React context: portfolio polling (4s interval)
│   │   └── WatchlistContext.tsx      # ✅ React context: watchlist CRUD
│   ├── public/                       # Static assets (empty — favicon/logo TBD)
│   ├── out/                          # Next.js export output (empty until built)
│   ├── .next/                        # Next.js dev build cache
│   └── node_modules/                 # npm dependencies
│   └── (missing files):
│       ├── package.json              # npm project config
│       ├── tsconfig.json             # TypeScript config
│       ├── next.config.ts            # Next.js config (output export, API proxy)
│       ├── app/                      # App router (pages + layout) — TBD
│       │   ├── layout.tsx            # Root layout: providers, header
│       │   ├── page.tsx              # Index page: main trading dashboard
│       │   ├── globals.css           # Global styles (Tailwind, dark theme)
│       │   └── api/                  # API route handlers (optional, for dev proxy)
│       └── components/               # React components (TBD)
│           ├── Watchlist.tsx
│           ├── Chart.tsx
│           ├── PortfolioHeatmap.tsx
│           ├── PositionsTable.tsx
│           ├── TradeBar.tsx
│           ├── ChatPanel.tsx
│           ├── ConnectionIndicator.tsx
│           └── PriceFlash.tsx
│
├── db/                               # Runtime volume mount target
│   └── finally.db                    # SQLite database (created at first startup, gitignored)
│
├── test/                             # E2E tests (Playwright)
│   ├── docker-compose.test.yml       # Test environment orchestration
│   ├── playwright.config.ts          # Playwright configuration
│   └── tests/                        # E2E test specs (TBD)
│       ├── smoke.spec.ts             # Fresh start, default watchlist
│       ├── trading.spec.ts           # Buy/sell flows
│       ├── portfolio.spec.ts         # Visualization + P&L accuracy
│       ├── chat.spec.ts              # Chat + AI auto-execution (with mock LLM)
│       └── resilience.spec.ts        # SSE reconnection, error handling
│
├── scripts/                          # Docker launch scripts
│   ├── start_mac.sh                  # Build & run container (macOS/Linux)
│   ├── stop_mac.sh                   # Stop container (macOS/Linux)
│   ├── start_windows.ps1             # Build & run container (Windows PowerShell)
│   └── stop_windows.ps1              # Stop container (Windows PowerShell)
│
├── planning/                         # Agent documentation (contracts for phases)
│   ├── PLAN.md                       # Full specification (this is the project plan)
│   ├── MARKET_DATA_SUMMARY.md        # Market data subsystem (completed)
│   └── archive/                      # Completed phase summaries
│
├── .planning/
│   └── codebase/                     # Codebase analysis documents (this directory)
│       ├── ARCHITECTURE.md           # Layers, data flow, entry points
│       ├── STRUCTURE.md              # Directory layout, naming, where to add code (you are here)
│       └── (other analysis docs: STACK.md, TESTING.md, etc.)
│
├── Dockerfile                        # Multi-stage: Node 20 (build frontend) → Python 3.12 (backend)
├── docker-compose.yml                # Optional: convenience wrapper (not used in prod)
├── .env.example                      # Template: OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK
├── .gitignore                        # Excludes node_modules, .venv, *.db, .env, etc.
├── CLAUDE.md                         # Project-level instructions (links to planning/PLAN.md)
├── README.md                         # User-facing README
└── LICENSE
```

## Directory Purposes

**`backend/app/market/`:**
- Purpose: Complete, tested market data subsystem
- Contains: Price cache, simulator, Massive client, SSE router, seed data
- Key files: `cache.py`, `interface.py`, `simulator.py`, `stream.py`
- Status: ✅ Implemented and tested

**`backend/app/api/`:**
- Purpose: FastAPI route handlers (request parsing, response formatting)
- Contains: Portfolio routes, watchlist routes, chat routes, prices routes, health check
- Key files: (to be created)
- Status: ⬜ Scaffolded (directory exists, no .py files)

**`backend/app/services/`:**
- Purpose: Business logic layer
- Contains: Trade execution, P&L calculation, position management, watchlist sync, chat flow, LLM calls
- Key files: (to be created)
- Status: ⬜ Scaffolded (directory exists, no .py files)

**`backend/app/db/`:**
- Purpose: Database schema, initialization, CRUD helpers
- Contains: Connection setup, schema creation, seed data, per-table CRUD modules
- Key files: (to be created)
- Status: ⬜ Scaffolded (directory exists, no .py files)

**`backend/app/llm/`:**
- Purpose: LLM integration (chat, structured output, auto-execution)
- Contains: LiteLLM client, structured output schema, chat service
- Key files: (to be created)
- Status: ⬜ Scaffolded (directory exists, no .py files)

**`backend/tests/market/`:**
- Purpose: Unit tests for market data subsystem
- Contains: Tests for all models, cache, simulator, data sources, factory
- Key files: `test_cache.py`, `test_simulator.py`, `test_models.py`
- Status: ✅ Implemented

**`frontend/lib/`:**
- Purpose: Data layer and utilities (React contexts, API client, TypeScript types)
- Contains: PriceStreamContext (SSE), PortfolioContext (polling), WatchlistContext (CRUD), api client, types, formatters
- Key files: `types.ts`, `api.ts`, `PriceStreamContext.tsx`, `PortfolioContext.tsx`, `WatchlistContext.tsx`
- Status: ✅ Implemented

**`frontend/app/` and `frontend/components/`:**
- Purpose: UI components and page structure
- Contains: Root layout with providers, main page, watchlist component, chart, portfolio display, heatmap, trade bar, chat panel
- Key files: (to be created)
- Status: ⬜ Scaffolded (directories don't exist yet)

**`planning/`:**
- Purpose: Agent documentation (project specification and phase summaries)
- Contains: PLAN.md (full spec), MARKET_DATA_SUMMARY.md (completed phase), archive of other phases
- Key files: `PLAN.md`
- Status: ✅ Planning docs committed

## Key File Locations

**Entry Points:**
- `backend/app/main.py` — FastAPI app factory, route registration, startup (MISSING)
- `frontend/app/layout.tsx` — Root layout with providers (MISSING)
- `frontend/app/page.tsx` — Main dashboard (MISSING)
- `backend/market_data_demo.py` — Standalone demo showing market data in isolation (exists for testing)

**Configuration:**
- `backend/pyproject.toml` — uv dependencies, pytest/ruff/coverage config
- `backend/.env` — Environment variables (OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK)
- `frontend/next.config.ts` — Next.js config: output export, dev proxy (MISSING)
- `frontend/tsconfig.json` — TypeScript config (MISSING)
- `frontend/package.json` — npm dependencies, build scripts (MISSING)

**Core Logic:**
- `backend/app/market/cache.py` — PriceCache: thread-safe in-memory store
- `backend/app/market/simulator.py` — GBM-based market simulator
- `backend/app/market/stream.py` — SSE router for live price pushes
- `backend/app/services/` — (TBD) Trade execution, portfolio valuation, watchlist sync
- `backend/app/llm/` — (TBD) Chat flow, structured outputs, trade auto-execution
- `frontend/lib/PriceStreamContext.tsx` — React context for SSE connection
- `frontend/lib/PortfolioContext.tsx` — React context for portfolio polling
- `frontend/lib/api.ts` — Fetch client for all `/api/*` endpoints

**Testing:**
- `backend/tests/market/test_*.py` — Market data unit tests
- `test/docker-compose.test.yml` — E2E test environment
- `test/tests/*.spec.ts` — Playwright E2E tests (TBD)

**Database:**
- `backend/app/db/init_db.py` — (TBD) Schema creation, seed data
- `backend/app/db/positions.py` — (TBD) Position CRUD
- `backend/app/db/trades.py` — (TBD) Trade log CRUD
- `backend/app/db/snapshots.py` — (TBD) Portfolio history CRUD
- `db/finally.db` — Runtime SQLite file (gitignored, volume-mounted)

## Naming Conventions

**Files:**
- Backend Python: `snake_case.py` (e.g., `market_data_demo.py`, `price_cache.py`)
- Frontend TypeScript/React: `PascalCase.tsx` for components, `camelCase.ts` for utilities (e.g., `PriceStreamContext.tsx`, `api.ts`, `usePriceHistory.ts`)
- Config files: `[name].config.[ext]` (e.g., `next.config.ts`, `vitest.config.ts`)

**Directories:**
- Functional grouping: `market/`, `api/`, `db/`, `services/`, `llm/` group code by responsibility
- Layered separation: Frontend `lib/` (data layer), `app/` (pages), `components/` (UI)
- Test mirrors source: `tests/market/test_*.py` mirrors `app/market/*.py`

**Python Classes:**
- `PascalCase` for classes (e.g., `PriceUpdate`, `PriceCache`, `MarketDataSource`, `SimulatorDataSource`)
- Exceptions: `PascalCase` + `Error` suffix (e.g., `TradeValidationError`, `InsufficientCashError`)

**Python Functions:**
- `snake_case` for module functions (e.g., `create_market_data_source()`, `create_stream_router()`)
- Private methods: `_snake_case` prefix (e.g., `_generate_events()`, `_rebuild_cholesky()`)

**TypeScript/React:**
- `PascalCase` for components and types (e.g., `PriceStreamContext`, `PriceUpdate`, `Portfolio`)
- `snake_case` for constants (e.g., `POLL_INTERVAL_MS = 4000`)
- `camelCase` for functions and variables (e.g., `sendChatMessage()`, `usePriceStream()`)

**Database Tables:**
- `snake_case` (e.g., `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`)
- User-scoped: all tables include `user_id` column (default: `"default"`)

## Where to Add New Code

**New Backend Endpoint:**
1. Define request/response types in comment or docstring (location TBD: `app/api/[route].py`)
2. Implement service logic in `app/services/` (e.g., `portfolio_service.py` for portfolio endpoints)
3. Create FastAPI route handler in `app/api/[route].py` (e.g., `app/api/portfolio.py`)
4. Import and register router in `app/main.py` (currently missing): `app.include_router(portfolio_router)`
5. Add tests in `backend/tests/api/test_[route].py` or `backend/tests/services/test_[service].py`

**New Frontend Component:**
1. Create component file in `frontend/components/[ComponentName].tsx`
2. Use existing contexts (`usePriceStream()`, `usePortfolio()`, `useWatchlist()`) from `frontend/lib/`
3. Import component in `frontend/app/page.tsx` or `frontend/app/layout.tsx`
4. Style with Tailwind CSS (classes in component or extracted to `globals.css`)
5. Add tests in `test/tests/[feature].spec.ts` (Playwright E2E)

**New Service:**
1. Create file in `app/services/[service_name].py`
2. Use dependency injection: accept `PriceCache`, database connection as constructor args
3. Define custom exceptions in `app/services/errors.py`
4. Write tests in `backend/tests/services/test_[service_name].py` (mock cache + db)

**New Database Query:**
1. Create CRUD module in `app/db/[table_name].py` (e.g., `app/db/positions.py`)
2. Use `app.db.connection.get_db()` (to be implemented) to get SQLite connection
3. Write helpers: `insert()`, `update()`, `delete()`, `get_by_id()`, `list_by_user()`
4. Write tests in `backend/tests/db/test_[table_name].py` (use in-memory SQLite for isolation)

**New Market Data Feature:**
- **Price cache logic:** `app/market/cache.py` — add methods as needed
- **Simulator feature:** `app/market/simulator.py` — modify GBM or event generation
- **Massive API integration:** `app/market/massive_client.py` — extend polling or parsing
- **SSE schema:** Update `app/market/models.py` → `PriceUpdate` fields; update `frontend/lib/types.ts` → `PriceUpdate` type

**New Test:**
- Backend unit: `backend/tests/[layer]/test_[module].py` — pytest
- E2E: `test/tests/[scenario].spec.ts` — Playwright
- Run with: `uv run --extra dev pytest` (backend) or `npx playwright test` (E2E)

**New Environment Variable:**
- Add to `.env.example`
- Read in `app/main.py` or `app/market/factory.py` with `os.environ.get(...)`
- Document in `backend/CLAUDE.md`

## Special Directories

**`backend/static/`:**
- Purpose: Frontend build output (mounted here by Docker)
- Generated: Yes (Next.js export → `frontend/out` → copied to `backend/static` in Dockerfile)
- Committed: No (gitignored)

**`db/`:**
- Purpose: Runtime SQLite database file
- Generated: Yes (created by backend on first startup if missing)
- Committed: No (gitignored)

**`backend/.venv/`:**
- Purpose: Virtual environment for uv project
- Generated: Yes (created by `uv sync`)
- Committed: No (gitignored)

**`frontend/node_modules/`:**
- Purpose: npm dependencies
- Generated: Yes (created by `npm install`)
- Committed: No (gitignored)

**`planning/archive/`:**
- Purpose: Completed phase summaries (moved here after archival)
- Generated: Yes (by agent workflow)
- Committed: Yes (historic record)

---

*Structure analysis: 2026-07-14*
