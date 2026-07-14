<!-- GSD:project-start source:PROJECT.md -->

## Project

**FinAlly — AI Trading Workstation**

FinAlly (Finance Ally) is a visually stunning, AI-powered trading workstation that streams live market data, lets a user trade a simulated $10,000 portfolio, and embeds an LLM chat copilot that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI assistant. It is the capstone project for an agentic AI coding course — built entirely by orchestrated coding agents to demonstrate production-quality full-stack output.

The market-data subsystem is already built and tested. This project builds the remaining platform — database, backend APIs, SSE routing, LLM chat, and the full frontend UI — to a demo-ready, end-to-end application.

**Core Value:** A user opens one URL and immediately gets a live, data-dense trading terminal where they can watch streaming prices, trade a simulated portfolio, and have an AI copilot execute trades and manage their watchlist through natural language — with the backend as the single authoritative source of all money math.

### Constraints

- **Tech stack**: FastAPI (Python, `uv`) backend; Next.js + TypeScript static export frontend; SQLite; Tailwind — fixed by PLAN.md and existing code
- **Single container, single port**: FastAPI serves API + SSE + static frontend on `:8000` — no CORS, one Docker container, one command to run
- **LLM provider**: LiteLLM → OpenRouter → Cerebras inference via the `cerebras` skill; structured outputs validated server-side before any auto-execution
- **Real-time**: SSE (`EventSource`) only — no WebSockets
- **Money precision**: cash, price, avg_cost rounded to cents at execution; all validation server-side
- **Conventions**: match existing `backend/app/market/` patterns (dataclasses, ABCs, DI via factories, ruff) and `frontend/lib/` context patterns — see `.planning/codebase/CONVENTIONS.md`

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.12+ - Backend server logic, market data simulation, portfolio computation
- TypeScript - Frontend application (React components)
- SQL - SQLite database schema and queries
- Bash - Deployment scripts (shell wrappers for Docker)
- PowerShell - Deployment scripts (Windows)

## Runtime

- Python 3.12+ (enforced by `pyproject.toml`)
- Node.js 20+ (frontend build, not deployed to container)
- `uv` (Python) - Replacement for pip/venv; fast, deterministic, lockfile-based
- `npm` (Node.js) - Frontend dependencies (built, not yet cataloged; `node_modules` present)
- `backend/uv.lock` - Present, pinned Python dependencies
- `frontend/package-lock.json` - Not found; frontend not yet scaffolded with package.json in repo root

## Frameworks

- FastAPI 0.115.0+ - Async web server, REST API, SSE streaming endpoints
- Uvicorn 0.32.0+ - ASGI server (HTTP + WebSocket, though SSE is one-way)
- Starlette - HTTP utilities (FastAPI's underlying library)
- Pydantic 2.x - Request/response validation, type checking
- Next.js - React framework for static export (build target: `output: 'export'`)
- React - UI components (implicit via Next.js)
- Tailwind CSS - Utility-first styling (configured but no config file found; may be in .next)
- pytest 8.3.0+ - Test runner for backend
- pytest-asyncio 0.24.0+ - Async test support
- pytest-cov 5.0.0+ - Coverage reporting
- React Testing Library or Jest - Frontend tests (not yet scaffolded)
- ruff 0.7.0+ - Fast Python linter and formatter (replaces flake8/black)
- Hatchling - Python package builder (via `[build-system]` in pyproject.toml)
- Rich 13.0.0+ - Terminal output formatting (used in market data demo)

## Key Dependencies

- `fastapi` 0.115.0+ - Core web framework for all REST endpoints and SSE
- `uvicorn[standard]` 0.32.0+ - Production ASGI server with all extras (uvloop, httptools)
- `numpy` 2.0.0+ - Numerical computation for GBM simulator (Cholesky decomposition, random variates)
- `massive` 1.0.0+ - Polygon.io REST client for real market data (optional at runtime; environment-gated)
- `pydantic` 2.x - Data validation via FastAPI integration
- `python-dotenv` - Loads `.env` file for `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`
- `rich` 13.0.0+ - Colored terminal output; used in `market_data_demo.py`
- `httptools`, `uvloop` - Performance optimizations bundled via `uvicorn[standard]`
- `typing-extensions` - Type hints backports for Python 3.12 compatibility
- `pytest` 8.3.0+ - Test framework
- `pytest-asyncio` 0.24.0+ - Async test fixtures
- `pytest-cov` 5.0.0+ - Coverage measurement

## Configuration

- `.env` (project root, gitignored) - Runtime configuration:
- No `.env.example` or documentation of env vars committed to repo; see `planning/PLAN.md` for reference
- `backend/pyproject.toml` - Python project metadata, dependencies, dev extras, tool configuration
- `backend/uv.lock` - Frozen dependency tree (v1, pinned)
- No `tsconfig.json`, `next.config.js`, or `tailwind.config.ts` found in frontend root (likely in `.next/build`)
- SQLite schema + seed logic not yet implemented (placeholder: `planning/PLAN.md` describes intended schema)
- Volume mount target: `db/` directory at project root (persists `finally.db` across container restarts)

## Platform Requirements

- Python 3.12+
- Node.js 20+ (frontend build only)
- `uv` package manager (not pip/venv)
- Docker (for containerized deployment)
- Docker container serving on port 8000
- Single process (no process manager like Gunicorn; Uvicorn runs directly)
- SQLite filesystem with persistent volume mount
- No external databases or caches yet (in-memory price cache in backend)

## Docker & Deployment

- Multi-stage Dockerfile (planned, not yet committed) per `PLAN.md`:
- Volume: `finally-data:/app/db` (SQLite persistence)
- Port: 8000 (single origin for frontend + all API routes)
- Base: Python 3.12 slim Docker image
- Node: 20 slim (build stage only)
- uvicorn: `0.32.0+` with `[standard]` extras (includes uvloop, httptools)

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Python: `snake_case.py` (e.g., `cache.py`, `simulator.py`, `factory.py`)
- TypeScript: `camelCase.ts` or `PascalCase.tsx` (e.g., `api.ts`, `types.ts`, `PriceStreamContext.tsx`)
- Test files: `test_*.py` for Python (pytest convention)
- Python: `snake_case` (e.g., `update()`, `get_price()`, `to_dict()`)
- TypeScript: `camelCase` (e.g., `formatCurrency()`, `toDate()`, `usePriceHistory()`)
- Private methods: prefix with `_` in both languages (e.g., `_add_ticker_internal()`, `_rebuild_cholesky()`)
- Python: `snake_case` (e.g., `event_probability`, `z_correlated`, `inFlight` becomes `in_flight`)
- TypeScript: `camelCase` (e.g., `disconnectTimer`, `inFlight`, `lastTimestamp`)
- Private/internal attributes: prefix with `_` (e.g., `_prices`, `_lock`, `_tickers`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `TRADING_SECONDS_PER_YEAR`, `DEFAULT_DT`, `DISCONNECTED_AFTER_MS`, `MAX_POINTS`)
- Python: `PascalCase` (e.g., `PriceUpdate`, `PriceCache`, `MarketDataSource`, `GBMSimulator`)
- TypeScript: `PascalCase` for types, interfaces, and components (e.g., `Direction`, `PriceStreamFrame`, `PriceStreamProvider`)
- Type aliases: `PascalCase` (e.g., `TradeSide`, `WatchlistAction`)

## Code Style

- **Backend:** Ruff formatter (enforced)
- **Frontend:** Assumed Prettier or similar (not explicitly configured in repo)
- **Backend (Ruff):** `ruff check app/ tests/` validates naming, imports, and style
- **Frontend:** No eslint config found in repo; conventions followed from Next.js defaults

## Import Organization

- Order followed (enforced by `I` in ruff):
- Example from `simulator.py`:
- Order observed:
- Example from `PriceStreamContext.tsx`:

## Error Handling

- Graceful degradation: skip malformed data instead of crashing (e.g., in `MassiveDataSource._poll_once()`, skip snapshots that lack `last_trade`)
- Network errors caught and logged; cache state unchanged (e.g., if Massive API fails, poller continues on next cycle)
- Custom error classes extend `Error` where semantics matter (backend doesn't show examples yet)
- Try/catch with fallback (e.g., `getPriceHistory()` catches backfill failures; empty-then-growing series is acceptable)
- Custom error class `ApiRequestError` extends `Error` with `status` property in `api.ts`
- JSON parsing wrapped in try/catch; malformed SSE frames are skipped, last good prices remain on screen
- Error messages propagated to UI state (e.g., `error: string | null` in context values)

## Logging

- Factory creates logger per module (e.g., `logger = logging.getLogger(__name__)` in `factory.py`)
- Info level for lifecycle events (e.g., "Market data source: Massive API (real data)" in `factory.py`)
- Scope: used for operational events (startup, data source selection), not verbose tracing

## Comments

- Non-obvious mathematical logic (e.g., GBM formula and time-step explanation in `simulator.py`)
- Architectural decisions and trade-offs (e.g., "this is the hot path — called every 500ms. Keep it fast" in `simulator.py:74`)
- Links to specification (`PLAN.md §3`, `PLAN.md §6`) when implementing spec requirements
- Clarifying why a code pattern is chosen (e.g., "This is a deliberate fetch-on-mount-then-poll" in `PortfolioContext.tsx`)
- All public class/function definitions include docstrings
- Format: one-line summary followed by multi-line explanation if needed
- Parameters and return types documented in docstrings
- Example from `cache.py`:

## Function Design

- Type hints required for all parameters (Python: `ticker: str`, TypeScript: `ticker: string`)
- Default values used for optional configuration (e.g., `timestamp: float | None = None`, `digits = 2`)
- Type hints required (e.g., `-> PriceUpdate`, `-> Promise<Portfolio>`)
- Immutable returns preferred (e.g., `PriceUpdate` is a frozen dataclass)
- None used explicitly for absent values (Python: `float | None`, TypeScript: `number | null`)

## Module Design

- Python: Import by name from module (e.g., `from app.market import PriceCache, create_market_data_source`)
- TypeScript: Named exports for functions and types; default export not used for components (e.g., `export function PriceStreamProvider(...)`, `export type Direction = ...`)
- Frozen dataclasses used for immutable value objects (e.g., `@dataclass(frozen=True, slots=True)` on `PriceUpdate`)
- Slots enable memory efficiency and prevent accidental attribute additions
- Properties used for derived values (e.g., `change`, `change_percent`, `direction` as properties on `PriceUpdate`)

## Dunder Methods

- Implement `__len__`, `__contains__` for collection-like classes (e.g., `PriceCache.__len__()`, `PriceCache.__contains__()`)
- Makes classes Pythonic and support `len()`, `in` operators

## Type Safety

- `from __future__ import annotations` enables forward references
- Union syntax: `float | None` (not `Optional[float]`)
- Generics: `dict[str, float]` (not `Dict[str, float]`)
- All public functions have type hints
- Strict null checking implicit (React/Next.js config)
- Union types for constrained strings: `type Direction = "up" | "down" | "flat"`
- Interfaces for API contracts: `interface PriceUpdate { ... }`
- Type imports used where possible: `import type { ... } from "./types"`

## Comments & Architectural Links

- `// Backend owns the numbers (§3)` in `format.ts`
- `// SSE is the source of truth for live prices (PLAN.md §10)` in `api.ts`
- `// Type hints enable multi-user scaling later (§3)` pattern

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

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

- **Backend computes all core numbers** — valuation, P&L, change %, price history; frontend only displays
- **SSE for live prices**, REST polling for slower-changing portfolio state
- **Market data is the seam** — in-memory cache (`PriceCache`) designed to move to Redis for multi-user scaling without changing downstream code
- **Layered separation** — market data (input), services (logic), API (output)
- **No global state** — dependency injection via factory functions and context providers

## Layers

- Purpose: Acquire, cache, and stream live price data
- Location: `app/market/`
- Contains: Data sources (simulator + Massive API), price cache, SSE streaming router
- Depends on: Python stdlib, numpy (for GBM), massive SDK (optional), FastAPI
- Used by: SSE endpoint, portfolio service (price lookups), API routes
- Purpose: Business logic — trades, portfolio valuation, watchlist management, LLM interaction
- Location: `app/services/` + `app/llm/`
- Contains: Trade execution, P&L math, watchlist CRUD, chat flow, LLM calls
- Depends on: Market data (price cache), database, LLM client
- Used by: API routes
- Purpose: HTTP endpoints, request/response handling, validation
- Location: `app/api/`
- Contains: Routes for portfolio, watchlist, chat, prices, health check
- Depends on: Services, market data
- Used by: Frontend, external clients
- Purpose: Persistence — user profiles, positions, trades, chat history, snapshots
- Location: `app/db/`
- Contains: Schema definitions, initialization, CRUD helpers per table
- Depends on: SQLite
- Used by: Services
- Purpose: Real-time subscription and state management
- Location: `frontend/lib/`
- Contains: React contexts for price stream (SSE), portfolio polling, watchlist CRUD; API client
- Depends on: Browser APIs (EventSource, fetch)
- Used by: Page components (TBD)

## Data Flow

### Primary Request Path: Trade Execution

### Secondary Flow: SSE Price Stream

### Tertiary Flow: Portfolio Polling

- **Prices**: Real-time source of truth in `PriceCache`; distributed via SSE to frontend; frontend does NOT poll REST for live updates
- **Portfolio**: Periodic REST polling every 4s; computed server-side (never client-side); updates trigger UI re-renders
- **Watchlist**: Loaded on mount + on-demand add/remove; initial paint includes price snapshot from cache
- **Chat**: Stateless per request; conversation history stored in SQLite; on response, trades are auto-executed and watchlist changes applied

## Key Abstractions

- Purpose: Immutable snapshot of a single ticker's state at a point in time
- Examples: `app/market/models.py:10`
- Pattern: Dataclass with computed properties (change, change_percent, direction); `to_dict()` for JSON serialization
- Used by: Cache, SSE stream, API responses, frontend types
- Purpose: Abstract interface for pluggable price sources
- Examples: `app/market/interface.py`
- Pattern: Abstract base class (ABC); implementations: `SimulatorDataSource`, `MassiveDataSource`; factory selects based on `MASSIVE_API_KEY` env var
- Used by: FastAPI app startup, price updates
- Purpose: Single source of truth for live prices; thread-safe; version counter for SSE change detection
- Examples: `app/market/cache.py`
- Pattern: Lock-protected dict; `update()` returns `PriceUpdate`; version increments on every write
- Used by: SSE stream, portfolio service (price lookups), API routes (watchlist validation)
- Purpose: Complete snapshot of user's financial state
- Examples: `frontend/lib/types.ts:58`
- Pattern: Immutable data structure (computed server-side); includes aggregates (total_value, total_unrealized_pnl) and details (positions array)
- Used by: PortfolioContext, header, positions table, heatmap

## Entry Points

- Location: Missing (to be implemented)
- Triggers: `uvicorn app.main:app` at container startup (Dockerfile CMD)
- Responsibilities:
- Location: `backend/market_data_demo.py`
- Triggers: `uv run market_data_demo.py`
- Responsibilities: Displays live terminal dashboard of simulated prices; demonstrates market data subsystem in isolation
- Location: `frontend/` (index page/root layout to be implemented)
- Triggers: Browser navigation to `http://localhost:8000` after backend starts
- Responsibilities:

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

### Avoided: Polling REST for Live Price Updates

### Avoided: Storing Realized P&L Separately

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| cerebras-inference | Use this to write code to call an LLM using LiteLLM and OpenRouter with the Cerebras inference provider | `.claude/skills/cerebras/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
