---
phase: 01-live-market-terminal
verified: 2026-07-14T22:13:13Z
status: human_needed
score: 21/21 must-haves verified (5/5 roadmap success criteria, 21/21 plan-level requirement IDs)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open http://localhost:8000 in a browser with the backend running; watch the watchlist for ~10-15 seconds"
    expected: "10 seeded ticker rows are visible, each price briefly flashes green (uptick) or red (downtick) and fades to transparent over ~500ms; sparklines are visibly populated (not blank) on first paint and grow over time"
    why_human: "CSS background-color transition/fade timing and visual sparkline rendering can only be confirmed by watching a real browser paint cycle; grep/curl confirmed the mechanism (direction-gated flash, prefers-reduced-motion skip, populated history data) but not the rendered pixels"
  - test: "Click a different watchlist row and observe the main chart panel"
    expected: "The chart briefly shows 'Loading chart…' (or swaps instantly if backfill is cached) then renders a populated filled-area chart for the newly selected ticker, growing live afterward; header symbol/price/change% updates to match"
    why_human: "Visual chart re-render and 'never empty' perception on ticker swap requires observing an actual browser paint, not just code/data-flow inspection"
  - test: "Resize the browser window to a tablet width (~768-1024px) and confirm the layout remains usable"
    expected: "Per UI-09 'functional on tablet', panels reflow/stack without being cut off or unusable; the AI-chat rail (hidden below `xl`) does not leave dead space"
    why_human: "Responsive layout quality/usability at a given breakpoint is a visual judgment; Tailwind breakpoint classes were confirmed present in code (`xl:block`, `md:grid-cols-3`) but their real rendered effect needs a human to view"
  - test: "Add an invalid ticker (e.g. '12345' or a 6+ letter string) via the watchlist input"
    expected: "An inline red error message appears directly beneath the input with the server's detail message, no toast/modal, field is not cleared"
    why_human: "Inline error rendering/positioning is a visual confirmation; the 400 response and error propagation path were verified via curl and code, but the rendered UI treatment needs a human to view"
---

# Phase 1: Live Market Terminal Verification Report

**Phase Goal:** A user opens http://localhost:8000 and sees a live, dark trading terminal streaming the 10 seeded tickers — an editable watchlist with flashing prices, server-computed change %, populated sparklines, and a clickable main detail chart.
**Verified:** 2026-07-14T22:13:13Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria — authoritative)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Opening localhost:8000 shows the dark terminal with the 10 default tickers streaming live prices that flash green/red and fade | ✓ VERIFIED (mechanism + data); visual fade needs human confirm | Live backend boot: `GET /` returned real Next export HTML containing "FinAlly"; `GET /api/watchlist` returned exactly the 10 seeded tickers (AAPL, AMZN, GOOGL, JPM, META, MSFT, NFLX, NVDA, TSLA, V) each with live price/direction; SSE stream (`GET /api/stream/prices`) emitted real per-500ms frames with `direction` up/down/flat; `WatchlistRow.tsx` gates a background flash strictly on `live.direction !== "flat"`, force-reflows, then transitions `background-color` to transparent over 500ms, skipped under `prefers-reduced-motion`. Colors sourced from locked Tailwind tokens (confirmed in compiled CSS: `.bg-positive`/`.bg-negative` = `rgb(63 185 80)`/`rgb(248 81 73)`). Routed to human verification for the rendered pixel confirmation only. |
| 2 | Each row shows server-computed change % and a sparkline that renders already-populated then keeps growing | ✓ VERIFIED | `GET /api/watchlist` and SSE frames both include `session_change_percent` computed server-side in `PriceUpdate.session_change_percent` (`backend/app/market/models.py`); `GET /api/prices/AAPL/history` returned real, non-empty `{timestamp,price}` points live; `Sparkline.tsx` takes a `points` prop from `usePriceHistory(ticker, live)` (backfill-then-extend hook, not reimplemented) and calls `setData`+`fitContent()` on every points change — renders populated on first paint by construction, never empty-then-appearing. |
| 3 | Clicking a ticker opens a larger detail chart that renders populated immediately then extends live | ✓ VERIFIED | `MainChartPanel.tsx` reads `selected` from `SelectedTickerContext` (set by `WatchlistRow`'s `onClick`), auto-selects `entries[0].ticker` when nothing is selected; `MainChart.tsx` consumes `usePriceHistory(selected, useTickerPrice(selected))` and calls `series.setData()` on every points change — same backfill-then-extend hook as sparklines, confirmed live via the `/api/prices/{ticker}/history` curl test above. |
| 4 | User can add a well-formed ticker and remove one; change persists; streaming starts/stops accordingly (removed-with-open-position keeps streaming) | ✓ VERIFIED | Live test: `POST /api/watchlist {"ticker":"pypl"}` → `{"ticker":"PYPL"}` (200), subsequently listed; `POST` with `"toolong123"` → 400 `{"detail":"Invalid ticker symbol ... must be 1-5 letters"}`; `DELETE /api/watchlist/PYPL` → `{"ticker":"PYPL"}`, removed. `watchlist_service.remove()` calls `watchlist_repo.has_open_position()` before calling `source.remove_ticker()` — position-held tickers are NOT untracked (unit-tested: `TestServiceRemove::test_remove_keeps_tracking_when_position_open`, passing). |
| 5 | Restarting the container preserves the watchlist (SQLite volume) and GET /api/health returns healthy | ✓ VERIFIED | Live test performed directly: booted uvicorn against a persistent `FINALLY_DB_PATH`, added then removed PYPL (net: still 10 tickers), killed the process, restarted uvicorn against the *same* DB file — `GET /api/health` returned `{"status":"ok",...}` and `GET /api/watchlist` returned exactly the same 10 original tickers (AAPL,AMZN,GOOGL,JPM,META,MSFT,NFLX,NVDA,TSLA,V), confirming SQLite persistence across process restart and idempotent re-seeding (`INSERT OR IGNORE`). |

**Score:** 5/5 roadmap success criteria verified (0 present-but-behavior-unverified; visual/browser confirmation items routed to human verification per Step 8, not counted as failures)

### Plan-Level Must-Haves (finer-grained, merged from all 6 PLAN.md frontmatter blocks)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DB creates 6 tables + seeds default user/tickers idempotently on startup | ✓ VERIFIED | `schema.sql` (6 `CREATE TABLE IF NOT EXISTS`), `database.py::initialize()`; live restart test confirmed idempotency |
| 2 | GET /api/health returns healthy JSON | ✓ VERIFIED | Live curl: `{"status":"ok","timestamp":...}` |
| 3 | Market-data task starts at startup, seeded from watchlist ∪ positions | ✓ VERIFIED | `main.py` lifespan: `db.initialize()` → `db.get_tracked_tickers()` → `source.start(tracked)`, in that order; `get_tracked_tickers()` unions `watchlist` and `positions` tables |
| 4 | Non-/api routes served from Next.js static export | ✓ VERIFIED | Live curl: `GET /` → 200, real "FinAlly" HTML; `GET /api/doesnotexist` → 404 (static mount does not shadow `/api/*`) |
| 5 | Cache captures session reference once per ticker, never overwritten | ✓ VERIFIED | `cache.py::update()` uses `self._session_refs.setdefault(ticker, rounded_price)`; unit-tested (`test_session_reference_stable_across_updates`, passing) |
| 6 | Cache keeps bounded ~600pt rolling history, in-memory only | ✓ VERIFIED | `deque(maxlen=MAX_HISTORY_POINTS=600)`; unit-tested FIFO eviction |
| 7 | to_dict() emits session_change_percent alongside existing keys | ✓ VERIFIED | `models.py::to_dict()` includes all keys; live SSE/REST payloads confirmed |
| 8 | npm run build produces static export with output:'export' | ✓ VERIFIED | `next.config.ts` sets `output: "export"`; `npm run build` completed, `frontend/out/index.html` exists |
| 9 | Dark Bloomberg-style multi-panel grid renders with locked theme tokens | ✓ VERIFIED (code+build); visual composition needs human confirm | `page.tsx` composes header/watchlist/chart/3-up/AI-rail grid; compiled CSS confirmed exact locked hex values for `bg-canvas`, `bg-positive`, `bg-negative`, `text-accent-yellow`, `text-up`, `text-down`, `text-ink-dim` |
| 10 | Header connection dot is live, driven by PriceStreamContext.status | ✓ VERIFIED | `ConnectionDot.tsx` reads `usePriceStream().status` exclusively, no independent state |
| 11 | Dev mode proxies /api/* to backend | ✓ VERIFIED | `next.config.ts` `rewrites()` → `http://localhost:8000/api/:path*` |
| 12 | GET /api/prices/{ticker}/history returns history for backfill | ✓ VERIFIED | Live curl returned populated `{timestamp,price}` array for AAPL |
| 13 | GET /api/watchlist returns tickers with session_change_percent | ✓ VERIFIED | Live curl confirmed shape and values |
| 14 | POST /api/watchlist validates/adds/idempotent/starts tracking | ✓ VERIFIED | Live curl (PYPL add succeeded, invalid rejected 400); unit tests pass |
| 15 | DELETE /api/watchlist/{ticker} removes but keeps tracking if position open | ✓ VERIFIED | Code + unit test (`test_remove_keeps_tracking_when_position_open`) |
| 16 | Watchlist grid: ticker, flashing price, session change%, sparkline | ✓ VERIFIED (code+data); visual flash needs human confirm | `WatchlistRow.tsx` full implementation read; all data sources are live/real (no hardcoded stubs) |
| 17 | Sparkline populated-then-growing via usePriceHistory | ✓ VERIFIED | `Sparkline.tsx` is a pure consumer of the `points` prop, never reimplements backfill |
| 18 | SSE-only after mount, no REST polling for live prices | ✓ VERIFIED | No `setInterval`/polling calls found in `WatchlistPanel.tsx`/`WatchlistRow.tsx`/`MainChartPanel.tsx`/`MainChart.tsx` (grepped) |
| 19 | Add ticker via inline input, remove via hover ×, server errors surfaced inline | ✓ VERIFIED (code+live 400); visual inline rendering needs human confirm | `AddTickerInput.tsx` catches `ApiRequestError`, renders `.message` inline in `text-negative`; live curl confirmed 400 detail message reaches this path |
| 20 | Clicking a ticker shows larger detail chart, backfilled then extends live | ✓ VERIFIED | `MainChartPanel.tsx`/`MainChart.tsx` code read; data flow confirmed live |
| 21 | First watchlist ticker auto-selected on load | ✓ VERIFIED | `MainChartPanel.tsx` effect: `if (selected === null && entries.length > 0) setSelected(entries[0].ticker)` |

**Score:** 21/21 plan-level must-haves verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/db/schema.sql` | 6 tables, IF NOT EXISTS | ✓ VERIFIED | All 6 tables present with exact PLAN.md §7 columns |
| `backend/app/db/database.py` | init/seed/tracked-set helpers | ✓ VERIFIED | `initialize()`, `get_tracked_tickers()` present and wired |
| `backend/app/api/health.py` | GET /api/health | ✓ VERIFIED | Live-tested, 200 healthy |
| `backend/app/main.py` | composition root | ✓ VERIFIED | Lifespan order correct, all Phase-1 routers registered, static mounted last |
| `backend/app/market/models.py` | session_reference/session_change_percent | ✓ VERIFIED | Additive fields present, backward compatible |
| `backend/app/market/cache.py` | session ref + history ring buffer + get_history | ✓ VERIFIED | All present, unit-tested, live-confirmed |
| `frontend/next.config.ts` | output:'export' + dev proxy | ✓ VERIFIED | Present |
| `frontend/tailwind.config.ts` | locked color tokens | ✓ VERIFIED | Confirmed in compiled CSS |
| `frontend/app/layout.tsx` | mounts 3 providers | ✓ VERIFIED | PriceStreamProvider → WatchlistProvider → SelectedTickerProvider |
| `frontend/app/page.tsx` | terminal grid | ✓ VERIFIED | Header/watchlist/chart/3-up/AI-rail composed |
| `frontend/components/ConnectionDot.tsx` | live status dot | ✓ VERIFIED | Reads real context state only |
| `frontend/lib/SelectedTickerContext.tsx` | shared selection seam | ✓ VERIFIED | Used by both WatchlistRow and MainChartPanel |
| `backend/app/api/prices.py` | history endpoint | ✓ VERIFIED | Live-tested |
| `backend/app/api/watchlist.py` | CRUD endpoints | ✓ VERIFIED | Live-tested (add/remove/invalid) |
| `backend/app/services/watchlist_service.py` | validation + orchestration | ✓ VERIFIED | Code read, unit-tested |
| `backend/app/db/watchlist_repo.py` | watchlist table CRUD + has_open_position | ✓ VERIFIED | Code read, unit-tested |
| `frontend/components/WatchlistPanel.tsx` | live watchlist assembly | ✓ VERIFIED | Renders real `useWatchlist().entries`, no hardcoded stubs |
| `frontend/components/WatchlistRow.tsx` | live row | ✓ VERIFIED | Full flash/selection/remove logic present |
| `frontend/components/Sparkline.tsx` | reusable minimal chart | ✓ VERIFIED | Pure consumer of `points` prop |
| `frontend/components/AddTickerInput.tsx` | inline add | ✓ VERIFIED | Real error surfacing wired |
| `frontend/components/MainChartPanel.tsx` | selection + header readout | ✓ VERIFIED | Real selection/auto-select/flash logic |
| `frontend/components/MainChart.tsx` | filled-area chart | ✓ VERIFIED | Real Lightweight Charts area series |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `main.py` lifespan | `db.initialize()` → `create_market_data_source().start()` | strict order | ✓ WIRED | Read directly in `create_app()`'s lifespan closure |
| `get_tracked_tickers()` | watchlist ∪ positions tables | SQL union | ✓ WIRED | `database.py` query, confirmed by code + unit test |
| Single `PriceCache` instance | lifespan, market source, stream/prices/watchlist routers | closure capture | ✓ WIRED | All four routers close over the same `cache` variable created once in `create_app()` |
| `PriceCache.update()` | `PriceUpdate(session_reference=...)` | constructor arg | ✓ WIRED | Confirmed in `cache.py` and live SSE payload (`session_change_percent` present and non-trivial) |
| `watchlist_service.add/remove` | DB row + `source.add_ticker/remove_ticker` | both mutated together | ✓ WIRED | Live-tested (PYPL added → tracked → removed → untracked) |
| `watchlist_service.remove` | `has_open_position()` check before untrack | conditional | ✓ WIRED | Unit-tested (`test_remove_keeps_tracking_when_position_open`) |
| `layout.tsx` | `PriceStreamProvider`/`WatchlistProvider`/`SelectedTickerProvider` | mount order | ✓ WIRED | Confirmed in source |
| `ConnectionDot` | `usePriceStream().status` | hook read | ✓ WIRED | No independent state |
| `WatchlistRow` | `useTickerPrice`, `usePriceHistory`, `useSelectedTicker`, `useWatchlist` | hook reads | ✓ WIRED | All four hooks consumed correctly |
| Row click | `SelectedTickerContext.setSelected` | `onClick` | ✓ WIRED | `× ` button uses `stopPropagation` so remove never selects |
| `MainChartPanel` | `SelectedTickerContext` + `useWatchlist().entries[0]` | auto-select effect | ✓ WIRED | Effect guarded to fire only while `selected === null` |
| `MainChart` | `usePriceHistory(selected, useTickerPrice(selected))` | prop | ✓ WIRED | Same hook pattern as sparklines, no re-derivation |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `WatchlistRow` | `points` (sparkline) | `usePriceHistory(ticker, live)` → `GET /api/prices/{ticker}/history` → `PriceCache.get_history()` | Yes — live curl returned real, non-empty, monotonically increasing `{timestamp,price}` series | ✓ FLOWING |
| `WatchlistRow` | `price`/`sessionChangePercent` | `useTickerPrice(ticker)` → live SSE frame → `PriceCache.update()` | Yes — live SSE curl showed real per-tick values with non-zero `session_change_percent` | ✓ FLOWING |
| `MainChart` | `points` | `usePriceHistory(selected, tick)` → same endpoint | Yes — same backend endpoint, confirmed live | ✓ FLOWING |
| `WatchlistPanel` | `entries` | `useWatchlist().entries` → `GET /api/watchlist` → DB + cache merge | Yes — live curl returned the 10 real seeded tickers with prices | ✓ FLOWING |

No hardcoded empty props (`=[]`, `={{}}`, `=null`) found at any call site in `page.tsx` for `WatchlistPanel`/`MainChartPanel` — both are rendered with no props, pulling all state from context.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend full test suite | `uv run --extra dev pytest -q` | 123 passed | ✓ PASS |
| Backend lint | `uv run --extra dev ruff check app/ tests/` | All checks passed | ✓ PASS |
| Frontend static export build | `npm run build && test -f out/index.html` | Build succeeded, only expected "rewrites not applied when exporting" warning | ✓ PASS |
| `GET /api/health` | live curl against booted app | `{"status":"ok",...}` | ✓ PASS |
| `GET /api/watchlist` | live curl | 10 seeded tickers with live prices/session_change_percent | ✓ PASS |
| `GET /api/prices/AAPL/history` | live curl | Populated history array | ✓ PASS |
| `POST /api/watchlist` valid | live curl `{"ticker":"pypl"}` | 200, `{"ticker":"PYPL"}` | ✓ PASS |
| `POST /api/watchlist` invalid | live curl `{"ticker":"toolong123"}` | 400, `{"detail":"Invalid ticker symbol..."}` | ✓ PASS |
| `DELETE /api/watchlist/PYPL` | live curl | 200, `{"ticker":"PYPL"}` | ✓ PASS |
| `GET /api/stream/prices` | live curl (2s window) | Real SSE frames with `session_change_percent` per ticker | ✓ PASS |
| `GET /` (static export) | live curl | 200, real Next.js HTML containing "FinAlly" | ✓ PASS |
| `GET /api/doesnotexist` | live curl | 404 (static mount does not shadow /api/*) | ✓ PASS |
| DB persistence across restart | boot → mutate → kill → reboot same DB file → curl | Watchlist unchanged (10 tickers), health healthy | ✓ PASS |

### Requirements Coverage

All 21 requirement IDs declared across the 6 phase plans (`DB-01..04, APP-01..04, MKT-01..05, WATCH-01..04, UI-01, UI-02, UI-09, UI-10`) are present in `.planning/REQUIREMENTS.md`'s v1 requirement list and its traceability table (all mapped to "Phase 1"). No orphaned requirements were found for Phase 1 in the traceability table.

| Requirement | Source Plan | Status | Evidence |
|-------------|------------|--------|----------|
| DB-01 | 01-01 | ✓ SATISFIED | schema.sql + init_db(), live-verified |
| DB-02 | 01-01 | ✓ SATISFIED | seed_default_data(), live-verified (10 tickers, $10k cash implied by schema default) |
| DB-03 | 01-01 | ✓ SATISFIED | Live restart-persistence test performed directly |
| DB-04 | 01-01 | ✓ SATISFIED | schema.sql user_id columns confirmed |
| APP-01 | 01-01, 01-04 | ✓ SATISFIED (Phase-1 scope) | health/stream/prices/watchlist routers registered and live-tested; portfolio/chat routers are explicitly out of Phase-1 scope (Phase 2/4 per ROADMAP) — see note below |
| APP-02 | 01-01, 01-03 | ✓ SATISFIED | Static export served, confirmed live, does not shadow /api/* |
| APP-03 | 01-01 | ✓ SATISFIED | Lifespan order confirmed in source |
| APP-04 | 01-01 | ✓ SATISFIED | Live-verified |
| MKT-01 | 01-02 | ✓ SATISFIED | Unit-tested + code-verified |
| MKT-02 | 01-02 | ✓ SATISFIED | Unit-tested + code-verified |
| MKT-03 | 01-02 | ✓ SATISFIED | Live SSE + REST payloads confirmed |
| MKT-04 | 01-04 | ✓ SATISFIED | Live-verified |
| MKT-05 | 01-04 | ✓ SATISFIED | Unit-tested + code-verified |
| WATCH-01 | 01-04 | ✓ SATISFIED | Live-verified |
| WATCH-02 | 01-04 | ✓ SATISFIED | Live-verified + unit-tested |
| WATCH-03 | 01-04 | ✓ SATISFIED | Unit-tested (`test_massive_mode_rejects_unpriceable_symbol`) + simulator path live-verified |
| WATCH-04 | 01-04 | ✓ SATISFIED | Unit-tested + live-verified |
| UI-01 | 01-05 | ✓ SATISFIED (code+data); visual flash → human_needed | See human verification items |
| UI-02 | 01-06 | ✓ SATISFIED (code+data); visual chart swap → human_needed | See human verification items |
| UI-09 | 01-03 | ✓ SATISFIED (code+build); visual/tablet → human_needed | See human verification items |
| UI-10 | 01-05 | ✓ SATISFIED | No polling code found; SSE-only confirmed |

**Note on APP-01:** `.planning/REQUIREMENTS.md` states the full APP-01 text as "registers all routers — stream, prices, portfolio, watchlist, chat, health," and its traceability table marks APP-01 as "Phase 1 | Complete." Portfolio and chat routers do not exist yet in this codebase (by design — `PORT-*` requirements map to Phase 2, `CHAT-*` to Phase 4, and `main.py`'s router-registration comment explicitly documents portfolio/chat as landing in later plans). This is a pre-existing documentation phrasing looseness in REQUIREMENTS.md/traceability (acknowledged in 01-01-PLAN.md's own text: "APP-01 is completed incrementally"), not a functional gap in Phase 1 — the phase's own ROADMAP success criteria and PLAN must-haves never require portfolio/chat routers. Flagged as informational, not a blocker.

### Anti-Patterns Found

None. Scanned all files created/modified across the 6 plans for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers and "coming soon"/"not yet implemented" copy — zero matches. The `PlaceholderPanel` component and its "coming in Phase 2/3/4" copy in `page.tsx` are intentional, correctly-scoped stand-ins for out-of-phase features (Positions, Heatmap, P&L, AI Assistant), not undone Phase-1 work.

### Behavioral Spot-Checks Summary

All automated checks pass: 123/123 backend tests, clean ruff lint, clean frontend static build, and 13/13 live curl-based end-to-end checks against a booted backend (health, watchlist CRUD, price history, SSE streaming, static serving, restart-persistence).

## Human Verification Required

The code, data wiring, and live end-to-end backend behavior are all confirmed working. What remains outside programmatic reach is purely visual/browser-rendering confirmation — per the verification methodology, "visual appearance" and "real-time behavior" always route to human verification regardless of how thoroughly the underlying mechanism is confirmed. See the `human_verification` list in the frontmatter for the 4 specific checks (price flash rendering, chart swap rendering, tablet responsive layout, inline error rendering).

## Gaps Summary

No gaps found. All 5 ROADMAP.md Success Criteria and all 21 plan-level must-haves are verified against the actual codebase — not just SUMMARY.md claims. Live end-to-end testing (booting the real backend, curling every endpoint, restarting to confirm persistence) was performed directly by this verification pass, going beyond static code reading. The only items not fully closed are inherently visual/browser-rendering confirmations (price flash animation, chart-swap transition, tablet layout, inline error styling) that cannot be observed via grep/curl and are routed to human verification per the standard methodology — this is a `human_needed` status, not a `gaps_found` status.

---

_Verified: 2026-07-14T22:13:13Z_
_Verifier: Claude (gsd-verifier)_
