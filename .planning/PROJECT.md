# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a visually stunning, AI-powered trading workstation that streams live market data, lets a user trade a simulated $10,000 portfolio, and embeds an LLM chat copilot that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI assistant. It is the capstone project for an agentic AI coding course — built entirely by orchestrated coding agents to demonstrate production-quality full-stack output.

The market-data subsystem is already built and tested. This project builds the remaining platform — database, backend APIs, SSE routing, LLM chat, and the full frontend UI — to a demo-ready, end-to-end application.

## Core Value

A user opens one URL and immediately gets a live, data-dense trading terminal where they can watch streaming prices, trade a simulated portfolio, and have an AI copilot execute trades and manage their watchlist through natural language — with the backend as the single authoritative source of all money math.

## Requirements

### Validated

<!-- Inferred from existing, tested code (backend/app/market/). Market Data Backend Summary: 73 tests passing, 84% coverage. -->

- ✓ **Market data source abstraction** — pluggable `MarketDataSource` ABC with simulator + Massive implementations, selected by `MASSIVE_API_KEY` — existing
- ✓ **GBM price simulator** — correlated geometric Brownian motion, per-ticker drift/volatility, random shock events, deterministic default params for unknown tickers — existing
- ✓ **Massive (Polygon.io) REST poller** — real market data when API key is present — existing
- ✓ **Thread-safe in-memory price cache** — `PriceCache` with version counter, latest/previous price, server-computed change/direction — existing
- ✓ **SSE price stream endpoint** — `GET /api/stream/prices` router pushing updates via version-based change detection — existing
- ✓ **Frontend data layer** — typed API client, SSE/portfolio/watchlist React contexts (`frontend/lib/`) — existing

### Active

<!-- Remaining PLAN.md scope, not yet built. All hypotheses until shipped and verified. -->

- [ ] **SQLite database** — schema + startup init + seed (users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages), single-user `default`, volume-mounted persistence
- [ ] **FastAPI app wiring** — `app/main.py`: router registration, DB init on startup, market-data background task, static frontend serving, `/api/health`
- [ ] **Price cache additive extensions** — session reference (open) price + bounded rolling history buffer + server-side change %; `GET /api/prices/{ticker}/history`
- [ ] **Portfolio APIs** — `GET /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/portfolio/history`; server-side trade execution, validation, avg-cost recompute, position-close-at-0, money rounding, snapshots (30s + post-trade)
- [ ] **Watchlist APIs** — `GET/POST/DELETE /api/watchlist`; symbol validation; tracked set = watchlist ∪ open positions
- [ ] **LLM chat** — `POST /api/chat` via LiteLLM → OpenRouter (Cerebras, `openrouter/openai/gpt-oss-120b`), structured output, auto-execution of trades + watchlist changes, 20-message history cap, `LLM_MOCK` mode
- [ ] **Frontend UI** — full terminal: watchlist grid w/ sparklines + flash, main chart, portfolio heatmap, P&L chart, positions table, trade bar, AI chat panel, header (value/cash/connection), dark theme
- [ ] **Docker & scripts** — multi-stage Dockerfile (Node build → Python serve), volume mount, start/stop scripts for macOS/Linux + Windows
- [ ] **Testing** — backend pytest for new units, frontend component tests, Playwright E2E with `LLM_MOCK=true`

### Out of Scope

- Authentication / multi-user — single hardcoded `user_id="default"`; schema is multi-user-ready but auth is not built (course simplification)
- Realized P&L ledger — only cash + `avg_cost`-based unrealized P&L; performance shown via `portfolio_snapshots` over time (PLAN.md §7)
- Limit / stop orders, order book, partial fills, fees — market orders only, instant fill (dramatically simpler portfolio math)
- WebSockets — SSE is sufficient for one-way server→client push
- Postgres / external DB server — SQLite is self-contained, zero-config for single-user
- Cloud deployment (App Runner / Terraform) — stretch goal only, not core build
- Token-by-token LLM streaming — Cerebras is fast enough that a loading indicator suffices

## Context

- **Brownfield.** Only the market-data subsystem is implemented (`backend/app/market/`, 8 modules, 73 passing tests). Everything else (`app/db/`, `app/api/`, `app/services/`, `app/llm/`, `app/main.py`, frontend pages/components) is scaffolded or missing. See `.planning/codebase/` for the full map.
- **Authoritative spec.** `planning/PLAN.md` is the build contract — vision, architecture, DB schema, API contracts, LLM integration, and 12 resolved design decisions all stand as written. `planning/MARKET_DATA_SUMMARY.md` documents the completed subsystem; `planning/archive/` has deeper market-data design docs.
- **Backend owns the core.** All valuation, P&L, change %, and price history are computed server-side; the frontend is a thin rendering layer that never derives core numbers. The in-memory price cache is the seam for future Redis-backed multi-user scaling.
- **Frontend contracts already exist.** `frontend/lib/types.ts` and `api.ts` define the API shapes the backend must satisfy — backend and frontend work should stay consistent with them.
- **Environment.** `OPENROUTER_API_KEY` required for chat; `MASSIVE_API_KEY` optional (simulator by default); `LLM_MOCK=true` for deterministic tests. `.env` lives at repo root (gitignored).

## Constraints

- **Tech stack**: FastAPI (Python, `uv`) backend; Next.js + TypeScript static export frontend; SQLite; Tailwind — fixed by PLAN.md and existing code
- **Single container, single port**: FastAPI serves API + SSE + static frontend on `:8000` — no CORS, one Docker container, one command to run
- **LLM provider**: LiteLLM → OpenRouter → Cerebras inference via the `cerebras` skill; structured outputs validated server-side before any auto-execution
- **Real-time**: SSE (`EventSource`) only — no WebSockets
- **Money precision**: cash, price, avg_cost rounded to cents at execution; all validation server-side
- **Conventions**: match existing `backend/app/market/` patterns (dataclasses, ABCs, DI via factories, ruff) and `frontend/lib/` context patterns — see `.planning/codebase/CONVENTIONS.md`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build full remaining platform to demo-ready as one milestone | Market-data done; user wants a working end-to-end app, not a partial slice | — Pending |
| `planning/PLAN.md` is authoritative | Existing spec is thorough and resolved; confirmed unchanged by user at init | — Pending |
| Market-data layer treated as Validated (not re-planned) | Already implemented, tested (73 tests), and reviewed | ✓ Good |
| SSE for prices, REST polling (4s) for portfolio | One-way push for fast-changing prices; polling for slower aggregate state | ✓ Good (frontend contracts already assume this) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-14 after initialization*
