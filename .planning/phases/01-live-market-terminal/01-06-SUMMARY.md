---
phase: 01-live-market-terminal
plan: 06
subsystem: ui
tags: [nextjs, react, typescript, lightweight-charts, tailwind, sse]

# Dependency graph
requires:
  - phase: 01-live-market-terminal
    provides: "Next.js terminal shell + placeholder MainChartPanel (01-03); locked frontend/lib contexts/hooks/api/types (PriceStreamContext, usePriceHistory, SelectedTickerContext, WatchlistContext, api.ts, types.ts); live GET /api/prices/{ticker}/history and SSE endpoints (01-04)"
provides:
  - "MainChart.tsx — TradingView Lightweight Charts filled-area line series, single instance disposed on unmount, styled per 01-UI-SPEC.md"
  - "MainChartPanel.tsx — selection wiring, first-ticker auto-select, live symbol/price/session-change-% header with flash, loading/empty states"
affects: [01-05 (watchlist row clicks drive selection this panel consumes)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Chart instance + series created once in a useRef pair inside a mount-only effect, disposed via chart.remove() on unmount; a separate effect calls series.setData() on every points change instead of recreating the chart"
    - "Price-flash mechanics without new global CSS: motion-safe:bg-{positive|negative}/25 applied only while flash state is non-null, combined with transition-colors duration-500 — under prefers-reduced-motion the motion-safe: variant never applies, leaving only text color to communicate direction"

key-files:
  created:
    - frontend/components/MainChart.tsx
  modified:
    - frontend/components/MainChartPanel.tsx

key-decisions:
  - "Used lightweight-charts v5's chart.addSeries(AreaSeries, options) API (not the removed v4 addAreaSeries) — confirmed against the installed package's typings.d.ts before writing the component"
  - "Distinguished 'watchlist still loading' from 'watchlist confirmed empty' via WatchlistContext's loading flag, so the empty state ('No chart to show') never flashes on initial mount/SSG prerender before the first GET /api/watchlist resolves — confirmed in the static export's prerendered HTML, which shows 'Loading chart…' (not the empty state) at build time"
  - "MainChart is only rendered once `selected` is non-null, so the underlying chart instance mounts exactly once per panel lifetime (not once per ticker) — ticker swaps reuse the same instance via setData(), matching the 'created once, disposed on unmount' acceptance criterion"

patterns-established:
  - "Pattern: flash-on-tick via motion-safe:/motion-reduce: Tailwind variants instead of matchMedia() JS or new global CSS classes — reusable for any future component needing a reduced-motion-aware flash without expanding the plan's files_modified scope"

requirements-completed: [UI-02]

coverage:
  - id: D1
    description: "Clicking a watchlist ticker shows a larger detail chart for that ticker"
    requirement: "UI-02"
    verification:
      - kind: other
        ref: "cd frontend && npm run build && test -f out/index.html"
        status: pass
    human_judgment: true
    rationale: "Confirming the click-to-select interaction and chart re-render requires a running backend (SSE + history endpoint) and a browser — deferred to the plan's documented full-stack manual verification step."
  - id: D2
    description: "The detail chart renders already-populated (backfilled from /api/prices/{ticker}/history) then extends live from the SSE frame"
    requirement: "UI-02"
    verification:
      - kind: other
        ref: "usePriceHistory(selected, tick) feeds MainChart's points prop; MainChart.setData() is called on every points change (code path, not independently re-implemented)"
        status: pass
    human_judgment: true
    rationale: "Backfill-then-live-extend behavior is only observable end-to-end against a running backend stream; static build/type-check confirms wiring, not runtime behavior."
  - id: D3
    description: "On load the first watchlist ticker is auto-selected so the chart is never empty when a watchlist exists"
    requirement: "UI-02"
    verification:
      - kind: other
        ref: "MainChartPanel useEffect: if (selected === null && entries.length > 0) setSelected(entries[0].ticker) — guarded to fire only once, guarded by watchlist row clicks (Plan 05) owning selection afterward"
        status: pass
    human_judgment: true
    rationale: "Auto-select firing correctly against a live watchlist fetch requires the backend + browser; code-level guard confirmed by reading, not executed against live data in this plan."
  - id: D4
    description: "npm run build produces a clean static export with the new components"
    requirement: "UI-02"
    verification:
      - kind: other
        ref: "cd frontend && npm run build && test -f out/index.html"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-14
status: complete
---

# Phase 1 Plan 06: Main Chart Panel Summary

**Filled-area Lightweight Charts detail chart wired to SelectedTickerContext with first-ticker auto-select, backfill-then-live-extend series, and a flashing symbol/price/change-% header — replacing the Plan 03 placeholder.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-14T21:58:00Z (worktree resume)
- **Completed:** 2026-07-14T22:02:51Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 replaced)

## Accomplishments
- Built `MainChart.tsx`: a single TradingView Lightweight Charts instance + area series, created once in a ref pair and disposed via `chart.remove()` on unmount, styled to the locked UI-SPEC tokens (accent-blue line, `rgba(32,157,215,0.35)` → transparent area gradient, transparent/inherited background, faint gridlines, neutral 12px axis text, hover crosshair). `setData()` runs on every `points` change so the chart renders populated immediately and grows in place as `usePriceHistory` appends live SSE ticks — no client-side derivation.
- Replaced the Plan 03 `MainChartPanel.tsx` placeholder: reads `selected` from `SelectedTickerContext`, auto-selects the first watchlist entry once (guarded so it only fires while nothing is selected, leaving Plan 05's row clicks in full control afterward), and feeds `usePriceHistory(selected, useTickerPrice(selected))` straight into `MainChart`.
- Header row per UI-SPEC: selected symbol (Heading 18/600), live tabular-nums price (Display 28/600) with a 500ms background flash on tick, and a `session_change_percent` pill badge — all reading the same SSE tick.
- Implemented the flash entirely with Tailwind's `motion-safe:`/`motion-reduce:` variants (no new global CSS, staying inside the plan's `files_modified` scope) — under `prefers-reduced-motion: reduce` the tinted background utility never applies, leaving text color alone to communicate direction, matching the UI-SPEC's reduced-motion requirement.
- Distinguished "watchlist still loading" (show a brief "Loading chart…") from "watchlist confirmed empty" (show "No chart to show") via `WatchlistContext.loading`, verified in the static export's prerendered HTML (shows "Loading chart…" at build time, not the empty state, since the client-side `GET /api/watchlist` hasn't resolved during SSG).

## Task Commits

Each task was committed atomically:

1. **Task 1: MainChart — filled-area Lightweight Charts series with backfill + live extend** - `ca06c08` (feat)
2. **Task 2: MainChartPanel — selection wiring, auto-select first ticker, header readout, states** - `a148428` (feat)

_No TDD tasks in this plan._

## Files Created/Modified
- `frontend/components/MainChart.tsx` - single chart+area-series instance (created once, disposed on unmount); `setData()` on every points change; styled per 01-UI-SPEC.md
- `frontend/components/MainChartPanel.tsx` - selection wiring (`SelectedTickerContext`), first-ticker auto-select, live header readout with flash, loading/empty states; replaces the Plan 03 placeholder

## Decisions Made
- Used lightweight-charts v5's `chart.addSeries(AreaSeries, options)` API rather than a v4-style `addAreaSeries()` call — confirmed against the installed package's `dist/typings.d.ts` before writing any code, since v5 changed the series-creation surface
- `WatchlistContext.loading` gates the empty-state check (`!loading && entries.length === 0`) so a fresh page load never briefly shows "No chart to show" before the first watchlist fetch resolves
- `MainChart` only mounts once `selected` is non-null, so the underlying chart instance is created exactly once per panel lifetime (ticker swaps reuse it via `setData()`), matching the plan's "chart is created once in a ref and disposed on unmount" acceptance criterion rather than remounting per ticker

## Deviations from Plan

None - plan executed exactly as written. `npm install` was required in this fresh worktree (no `node_modules/` present, consistent with 01-03-SUMMARY noting `node_modules` is gitignored) — this is expected setup, not a deviation from the plan's action text, and is the same sandbox-EROFS pattern already documented in 01-03-SUMMARY (worked around with the sandbox override for `npm install`/`npm run build`, same as that plan).

## Issues Encountered
- `npm run build` initially failed inside the sandbox with `EROFS` writing to the shared `~/.npm/_cacache` directory during Next's internal TypeScript-package self-check step — the same sandbox filesystem restriction noted in 01-03-SUMMARY's Issues Encountered. Re-ran with the sandbox override; build completed cleanly both times (Task 1 and Task 2 verification).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `MainChartPanel` and `MainChart` are live and ready for full-stack manual verification once both the backend (`/api/stream/prices`, `/api/prices/{ticker}/history`, `/api/watchlist`) and the Plan 05 watchlist row-click wiring are running together
- `frontend/lib/*` contracts were read-only for this plan and remain untouched, preserving the parallel-plan seam with Plan 05
- Full-stack manual verification (auto-select firing against a live watchlist, click-to-swap re-backfill, live flash against real SSE ticks) was not performed in this plan — requires the backend running and Plan 05's watchlist rows wired to `SelectedTickerContext.setSelected`; deferred to the plan's own "Manual (full stack)" verification step

## Self-Check: PASSED

- FOUND: frontend/components/MainChart.tsx
- FOUND: frontend/components/MainChartPanel.tsx
- FOUND: commit ca06c08
- FOUND: commit a148428

---
*Phase: 01-live-market-terminal*
*Completed: 2026-07-14*
