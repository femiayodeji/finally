# Walking Skeleton — FinAlly (AI Trading Workstation)

**Phase:** 1
**Generated:** 2026-07-14

## Capability Proven End-to-End

A user opens `http://localhost:8000`, the FastAPI process serves the static Next.js dark-terminal shell, the browser's single `EventSource('/api/stream/prices')` connects, the header connection dot turns green, and at least one live SSE price frame for the 10 seeded tickers renders — with the watchlist read from the SQLite database that was schema-created and seeded on startup and that survives a restart.

This exercises every architectural layer at its thinnest: SQLite init/seed → market-data background task (already built) → in-memory `PriceCache` → SSE stream router (already built) → FastAPI static serving → Next.js static export → React SSE context → visible UI.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI (Python 3.12, `uv`) | Fixed by PLAN.md §3; market subsystem already built on it |
| App composition | Single `app/main.py` with an ASGI **lifespan** that (1) inits+seeds SQLite, (2) builds `PriceCache`, (3) `create_market_data_source(cache)` and `start(watchlist ∪ positions)`, (4) registers routers, (5) mounts static export | DB must be ready before the market task reads the watchlist (PLAN.md §7); no module-level singletons (CONVENTIONS.md) |
| Data layer | SQLite via stdlib `sqlite3`, file at `db/finally.db`, all 6 tables, every table `user_id` default `"default"` | PLAN.md §7; zero-config, volume-mounted; no new backend dependency |
| Real-time transport | SSE (`EventSource`) via the existing `create_stream_router` | PLAN.md §6/§10; no WebSockets |
| Frontend framework | Next.js (App Router) + TypeScript, `output: 'export'` (static), Tailwind CSS dark theme | PLAN.md §3/§10, CONTEXT D-09; single-origin static serving, no CORS |
| Dev integration | `next.config.ts` `rewrites` proxying `/api/*` → `http://localhost:8000` for local dev; prod serves the export from FastAPI | `frontend/lib/api.ts` comment references `next.config.ts`; same-origin in prod |
| Charting | TradingView Lightweight Charts (canvas) for sparklines **and** the main chart | CONTEXT D-01; streaming perf for 10+ series at ~500ms |
| Directory layout | `backend/app/{db,api,services,market}` (market built); `frontend/{app,components,lib}` (lib built) | STRUCTURE.md; keep `frontend/lib/*` contracts untouched |

## Stack Touched in Phase 1

- [x] Project scaffold — Next.js TS + Tailwind + `output:'export'`; backend `app/main.py` entrypoint (Plan 01, Plan 03)
- [x] Routing — `GET /api/health`, existing `GET /api/stream/prices`, plus `/api/prices/*` and `/api/watchlist*` (Plan 01, Plan 04)
- [x] Database — real write (schema create + seed user + 10 tickers on startup) AND real read (watchlist load to seed tracking and serve `GET /api/watchlist`) (Plan 01, Plan 04)
- [x] UI — one interactive element wired to the API: the watchlist add-ticker input (`POST /api/watchlist`) and hover-remove (`DELETE`), plus click-to-select chart (Plan 05, Plan 06); the header connection dot is live from the SSE context in the shell (Plan 03)
- [x] Run — documented local full-stack run: `cd backend && uv run uvicorn app.main:app --port 8000` serving the built `frontend/out`; dev mode `npm run dev` with the `/api` proxy

## Out of Scope (Deferred to Later Slices)

- Trading / positions / trade bar / live header financials → Phase 2 (placeholder panels only now)
- Portfolio heatmap + P&L-over-time chart + `portfolio_snapshots` writer → Phase 3
- AI copilot chat + LLM integration → Phase 4
- Dockerfile, volume packaging, start/stop scripts → Phase 5
- Test hardening (Playwright E2E, full frontend/back coverage) → Phase 6 (Phase 1 keeps the existing 73 market tests green and adds light smoke coverage only)
- Realized P&L ledger — permanently out of scope (unrealized only)

## Subsequent Slice Plan

Each later phase adds one vertical slice without changing the skeleton's architectural decisions:

- Phase 2: Buy/sell with instant fills, positions table, live header financials
- Phase 3: P&L-colored heatmap + portfolio-value-over-time chart (durable snapshots)
- Phase 4: AI copilot chat that analyzes the portfolio and auto-executes trades/watchlist changes
- Phase 5: One-command Docker launch with persistent volume + start/stop scripts
- Phase 6: Backend + frontend + Playwright E2E hardening
