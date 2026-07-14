# Phase 1: Live Market Terminal - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Phase Boundary

A user opens `http://localhost:8000` and sees a live, dark trading terminal streaming the 10 seeded tickers: an editable watchlist with flashing prices, server-computed session change %, populated sparklines, and a clickable main detail chart. This phase also lands the foundational plumbing every later slice depends on — SQLite init + seed, `app/main.py` app wiring, static frontend serving, `/api/health`, and the additive market-data cache extensions (session reference price, rolling history, server change %, `/history` endpoint, tracked-set union).

**In scope:** DB-01..04, APP-01..04, MKT-01..05, WATCH-01..04, UI-01, UI-02, UI-09, UI-10.
**Not in this phase:** trading/positions (Phase 2), heatmap/P&L chart (Phase 3), AI chat (Phase 4), Docker/scripts (Phase 5), test hardening (Phase 6). The layout builds *placeholders* for those panels but wires no behavior.

</domain>

<decisions>
## Implementation Decisions

### Charting
- **D-01:** Use **TradingView Lightweight Charts** (canvas) for BOTH the watchlist sparklines and the main detail chart. Chosen for streaming perf with 10+ series updating ~500ms and to satisfy PLAN.md §10 "canvas-based charting library preferred." Single library for both surfaces.
- **D-02:** Charts backfill from `GET /api/prices/{ticker}/history` on load (render populated immediately), then extend live from the SSE frame. Never derive series client-side beyond appending streamed points.

### Watchlist Add/Remove UX
- **D-03:** Add via a small **always-visible inline ticker input** in the watchlist panel (type symbol + Enter). Remove via a **hover-revealed '×'** on each row. Fast, dense, terminal-like — no modal.
- **D-04:** Add input normalizes to uppercase and relies on server-side validation (`POST /api/watchlist`, 1–5 letters); surface the server's error inline on rejection. Duplicate adds are idempotent (no error UI needed).

### Phase 1 Layout Shell
- **D-05:** Build the **full Bloomberg-style multi-panel grid now** (header, watchlist, main chart) with **empty placeholder panels** for later phases (portfolio heatmap, positions table, P&L chart, AI chat). Later phases fill panels without relayout.
- **D-06:** Header renders live total-value/cash **placeholders** and a **working connection-status dot** (green/yellow/red) driven by `PriceStreamContext.status` — the dot is real in Phase 1; portfolio figures are stubs until Phase 2.

### SSE Payload / Change % (integration — locked fact)
- **D-07:** The watchlist and header display the **session-open-based change %** — the SSE/REST field the frontend already types as `session_change_percent` (`frontend/lib/types.ts`). This is stable across reloads because its reference (session open price) lives server-side (PLAN.md §10). The existing per-tick `change_percent` (latest vs previous) stays available but is NOT the number shown as the row's "change %."
- **D-08:** MKT extensions must add the session reference price and emit `session_change_percent` from `PriceUpdate.to_dict()` so the existing frontend contract is satisfied without changing `types.ts`. Keep both `change`/`change_percent` (vs previous) and `session_change_percent` (vs session open) in the payload.

### Frontend Scaffolding (context, not a user preference)
- **D-09:** The Next.js project is not yet scaffolded — only `frontend/lib/` exists (no `package.json`, `app/`, or config; stale `.next`/`node_modules` present). Phase 1 must scaffold the Next.js TypeScript app with `output: 'export'`, Tailwind, and a dev proxy for `/api/*` → backend (per `api.ts` comment referencing `next.config.ts`). Planner/researcher own the exact setup.

### Claude's Discretion
- Chart default + style (not selected for discussion): auto-select the **first watchlist ticker** on load; main chart is a **filled-area line**; sparklines are minimal lines colored by direction. Adjustable during UI phase.
- Exact grid proportions, spacing, and placeholder styling — follow PLAN.md §2/§10 aesthetic (dark `#0d1117`/`#1a1a2e`, accents `#ecad0a`/`#209dd7`/`#753991`) and the `/gsd-ui-phase 1` design contract.
- Price-flash animation mechanics (CSS class + transition timing ~500ms fade).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Authoritative spec
- `planning/PLAN.md` — full build contract. Especially §2 (UX/visual design + colors), §3 (backend owns the core), §6 (market data, price cache extensions, SSE), §8 (API endpoints, watchlist validation), §10 (frontend design, SSE-as-source-of-truth, change % stable across reloads).
- `planning/MARKET_DATA_SUMMARY.md` — what the built market-data subsystem provides and how to consume it.

### Codebase map
- `.planning/codebase/ARCHITECTURE.md` — layers, data flow (trade path, SSE flow, portfolio polling), entry points, anti-patterns.
- `.planning/codebase/STRUCTURE.md` — directory layout, what's implemented vs scaffolded.
- `.planning/codebase/CONVENTIONS.md` — Python (dataclasses, ABCs, DI via factories, ruff) and TS/React (named exports, contexts) conventions to match.
- `.planning/codebase/CONCERNS.md` — unbuilt surface area, secrets handling (`.env` at root).

### Existing contracts Phase 1 must satisfy (read the actual files)
- `frontend/lib/types.ts` — API/SSE type contracts (note `PriceUpdate` carries both `change_percent` and `session_change_percent`; `WatchlistEntry` shows `session_change_percent`). Comment cites "BUILD_PLAN.md §8" — this means `planning/PLAN.md §8` (stale name).
- `frontend/lib/api.ts` — same-origin `/api/*` client; expects a dev proxy via `next.config.ts`.
- `frontend/lib/PriceStreamContext.tsx` — shared single `EventSource('/api/stream/prices')`; `status` = connected/reconnecting/disconnected drives the header dot.
- `frontend/lib/WatchlistContext.tsx`, `frontend/lib/usePriceHistory.ts`, `frontend/lib/format.ts` — watchlist CRUD state, history backfill hook, display formatting.
- `backend/app/market/stream.py` — SSE router (`create_stream_router`), version-based change detection, 500ms cadence.
- `backend/app/market/cache.py`, `models.py`, `seed_prices.py` — `PriceCache` API + `PriceUpdate.to_dict()` (the surfaces MKT-01..05 extend), default tickers/seed params.
- `backend/CLAUDE.md` — how to consume the market-data subsystem (imports, PriceCache/PriceUpdate/MarketDataSource API).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/market/*` — fully built and tested (73 tests): `PriceCache`, `PriceUpdate`, `MarketDataSource` (+ simulator/Massive), `create_market_data_source`, `create_stream_router`, seed prices. Phase 1 consumes these; MKT-01..05 *extend* the cache/models (session ref price, rolling history buffer, `session_change_percent`, `/prices/{ticker}/history`, tracked-set union) — do not rebuild.
- `frontend/lib/` — API client, types, and three React contexts (PriceStream via SSE, Portfolio via 4s polling, Watchlist CRUD) plus `usePriceHistory` and `format` helpers already implemented. UI components render against these.

### Established Patterns
- Backend: factory-injected dependencies (no module singletons), frozen `@dataclass(frozen=True, slots=True)` value objects with computed properties + `to_dict()`, ruff-enforced style, `from __future__ import annotations`.
- Frontend: `"use client"` context providers mounted near root, named exports, `import type`, same-origin `/api/*`, SSE is the live-price source of truth (no REST polling for prices — UI-10).

### Integration Points
- `app/main.py` (new) wires: DB init+seed (before market task), router registration (existing stream router + new prices/watchlist/health routers), `create_market_data_source(cache)` started from watchlist ∪ positions, and static serving of the Next.js export.
- `PriceUpdate.to_dict()` (cache/models) is the seam where `session_change_percent` must appear for the frontend contract.
- Watchlist mutations must update the market-data tracked set (add/remove ticker) per MKT-05.

</code_context>

<specifics>
## Specific Ideas

- Terminal aesthetic per PLAN.md §2: dark backgrounds (`#0d1117` / `#1a1a2e`, no pure black), muted gray borders, price-flash green/red fading over ~500ms, connection-status dot in the header, data-dense desktop-first layout.
- Accent palette: yellow `#ecad0a`, blue `#209dd7`, purple `#753991` (submit buttons).
- Sparklines must render already-populated (backfilled) then keep growing — never start empty.

</specifics>

<deferred>
## Deferred Ideas

- Trading (trade bar, instant fills), positions table, live header financials → **Phase 2**.
- Portfolio heatmap + P&L-over-time chart → **Phase 3**.
- AI copilot chat panel → **Phase 4**.
- These get placeholder panels in the Phase 1 grid but no behavior.

None of the discussion introduced out-of-phase scope creep.

</deferred>

---

*Phase: 1-Live Market Terminal*
*Context gathered: 2026-07-14*
