---
phase: 01-live-market-terminal
plan: 05
subsystem: ui
tags: [nextjs, react, typescript, tailwind, lightweight-charts, watchlist, sse]

# Dependency graph
requires:
  - phase: 01-live-market-terminal
    provides: "frontend/lib/* locked contracts (PriceStreamContext, WatchlistContext, usePriceHistory, SelectedTickerContext, api, format, types) from Plan 03; frontend/components/{Panel,WatchlistPanel-placeholder} from Plan 03; live REST APIs (GET/POST/DELETE /api/watchlist, GET /api/prices/{ticker}/history) from Plan 04"
provides:
  - "Live, editable watchlist panel: ticker rows with backfilled+growing sparklines, live flashing prices, server session_change_percent, inline add, hover-remove"
  - "Sparkline.tsx — reusable Lightweight Charts minimal-line component (ticker/direction-agnostic, consumes a PricePoint[] series)"
affects: [01-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-row Lightweight Charts instance created once in a ref, disposed on unmount (bounds memory per threat T-05-02)"
    - "Price flash via imperative style writes (transition:none -> set flash color -> force reflow -> transition:500ms -> transparent) rather than a global CSS keyframe, so no shared/global file needed editing"
    - "Row falls back from live SSE tick (useTickerPrice) to the REST initial-paint snapshot on WatchlistEntry until the stream delivers a frame for that ticker"
    - "-mx-4 row-list wrapper cancels Panel's 16px padding so rows/hover-remove/selection tint bleed to the panel edge, while each row keeps its own 12px horizontal padding per UI-SPEC"

key-files:
  created:
    - frontend/components/Sparkline.tsx
    - frontend/components/WatchlistRow.tsx
    - frontend/components/AddTickerInput.tsx
  modified:
    - frontend/components/WatchlistPanel.tsx

key-decisions:
  - "Price-flash implemented via direct DOM style writes + forced reflow instead of a global CSS @keyframes rule, keeping the change entirely inside this plan's files_modified scope (no edits to the shared frontend/app/globals.css)"
  - "session_change_percent's own sign (not the SSE tick's transient up/down/flat direction) drives the price/percent text color, per D-07 — reuses format.ts's directionColorClass by mapping sign -> synthetic Direction"
  - "WatchlistRow accepts the full WatchlistEntry (not just a ticker string) so it has the REST initial-paint price/change/direction snapshot to render before the first SSE frame for that ticker arrives"

requirements-completed: [UI-01, UI-10]

coverage:
  - id: D1
    description: "npm run build produces a static export with the live watchlist panel"
    requirement: "UI-01"
    verification:
      - kind: other
        ref: "cd frontend && npm run build && test -f out/index.html"
        status: pass
    human_judgment: false
  - id: D2
    description: "Sparkline is a thin consumer of usePriceHistory (backfill+extend), not a reimplementation, and is created once/disposed on unmount"
    requirement: "UI-01"
    verification:
      - kind: other
        ref: "Sparkline.tsx takes points: PricePoint[] as a prop (never calls getPriceHistory itself); chart/series created once in a useEffect with [] deps, chart.remove() in the cleanup"
        status: pass
    human_judgment: false
  - id: D3
    description: "Row displays session_change_percent (not change_percent), signed and sign-colored"
    requirement: "UI-01"
    verification:
      - kind: other
        ref: "WatchlistRow.tsx reads live?.session_change_percent ?? entry.session_change_percent, formats via formatPercent (always signed), colors via directionColorClass on a sign-derived Direction"
        status: pass
    human_judgment: false
  - id: D4
    description: "Price flash fades green/red on tick direction and is skipped under prefers-reduced-motion; live streaming, click-to-select, hover-remove, inline add-error, and SSE-only pricing all behave correctly end-to-end"
    requirement: "UI-10"
    verification:
      - kind: other
        ref: "WatchlistRow.tsx checks window.matchMedia('(prefers-reduced-motion: reduce)').matches before writing any flash style; no setInterval/poll call exists in WatchlistPanel/WatchlistRow/AddTickerInput (grep confirms only a doc comment mentions polling, as a negative statement)"
        status: pass
    human_judgment: true
    rationale: "Confirming the flash actually fades on screen, sparklines render populated-then-growing, and add/remove work against a live backend requires running the full stack (backend on :8000 + npm run dev) and observing the browser — deferred to the plan's own 'Manual (full stack)' verification step."

# Metrics
duration: 25min
completed: 2026-07-14
status: complete
---

# Phase 1 Plan 05: Watchlist Panel (Live Rows, Sparklines, Add/Remove) Summary

**Filled the watchlist panel with dense 40px rows that stream live flashing prices and server-computed session change % via `useTickerPrice`/`usePriceHistory`, plus an inline uppercase-on-type add-ticker input and hover-revealed remove control — SSE is the sole live-price source after mount, REST/`WatchlistEntry` only supplies the initial-paint snapshot.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2
- **Files modified:** 4 (3 new components, 1 replaced placeholder body)

## Accomplishments

- `Sparkline.tsx` — a minimal ~60×24px Lightweight Charts line series (no axes/gridlines/crosshair/price-scale), colored `positive`/`negative`/`neutral` by direction, created once per mount in a ref and disposed on unmount; consumes a `PricePoint[]` prop and calls `setData` + `fitContent()` on every update, so it renders populated on first paint (never empty-then-appearing) and grows as `usePriceHistory` extends the series
- `WatchlistRow.tsx` — one 40px row per ticker: ticker (14/600) left, sparkline middle, price (tabular-nums) stacked over signed `session_change_percent` (D-07, colored by its own sign) on the right; a background flash (positive/negative 25% opacity → transparent over 500ms ease-out) fires only on genuine SSE ticks with a non-flat direction, and is skipped entirely under `prefers-reduced-motion: reduce`; clicking the row (anywhere except the remove control) sets `SelectedTickerContext`, and a 3px accent-blue left border + tint marks the selected row; a hover-revealed 44px-hit-area "×" (`stopPropagation`) calls `useWatchlist().remove()`
- `AddTickerInput.tsx` — full-width 40px input, uppercases as typed, submits on Enter via `useWatchlist().add()`, surfaces `ApiRequestError.message` (the server's `detail`) inline in `negative` red beneath the input, clears the field and any prior error on success; duplicate adds resolve without error (server-side idempotency) so nothing special is needed client-side
- `WatchlistPanel.tsx` — replaced the Plan 03 placeholder: renders `AddTickerInput` then maps `useWatchlist().entries` to `WatchlistRow` in persisted order, or the locked empty state ("Your watchlist is empty" / "Type a ticker symbol above and press Enter to start streaming.") when the list is empty and not loading; the row list bleeds to the panel's edges (`-mx-4`, canceling `Panel`'s 16px padding) so the selected-row tint and remove-hit-area reach the panel border while each row keeps its own 12px horizontal padding

## Task Commits

Each task was committed atomically:

1. **Task 1: Sparkline + WatchlistRow** — `a7cf960` (feat)
2. **Task 2: AddTickerInput + WatchlistPanel assembly** — `fa8415c` (feat)

_No TDD tasks in this plan._

## Files Created/Modified

- `frontend/components/Sparkline.tsx` — created; reusable minimal Lightweight Charts line, one instance per row
- `frontend/components/WatchlistRow.tsx` — created; live row with flash, session change %, sparkline, selection, remove
- `frontend/components/AddTickerInput.tsx` — created; inline uppercase-on-type add with inline server-error surfacing
- `frontend/components/WatchlistPanel.tsx` — replaced Plan 03's placeholder body with the live assembly above

## Decisions Made

- Implemented the price flash via direct imperative style writes (set flash-color background with `transition: none`, force a reflow via `el.offsetHeight`, then set `transition: background-color 500ms ease-out` and `background-color: transparent`) instead of adding a global `@keyframes` rule to `frontend/app/globals.css`. This keeps the entire implementation inside this plan's `files_modified` scope — no edits to any file outside the four listed, and no risk of clashing with a concurrent sibling plan (01-06, main chart) that may also want flash-style CSS on the same shared stylesheet.
- `session_change_percent`'s own sign (not the transient SSE tick `direction`) drives the price/percent text color — computed a synthetic `Direction` from the sign and reused the locked `format.ts` `directionColorClass` rather than writing a new color helper, per D-07 and the "don't reimplement locked lib" instruction.
- `WatchlistRow` takes the full `WatchlistEntry` (not a bare ticker string) so it has a price/change/direction value to render immediately from the REST initial-paint snapshot, falling back seamlessly to `useTickerPrice()`'s live SSE value the moment a frame for that ticker arrives — avoids an empty/dash flash between mount and first SSE tick for tickers the stream is already tracking.

## Deviations from Plan

None — plan executed exactly as written. The flash-implementation choice (imperative style writes vs. a global CSS class) is a within-scope technical decision, not a deviation from any `<action>` instruction — the plan's action text describes the *visual* behavior (25% opacity flash fading over 500ms ease-out, skip under reduced motion) without mandating the CSS mechanism, and PLAN.md §10's "briefly apply a CSS class with background color transition" note is satisfied in spirit (a transition is applied via style, imperatively, not a persistent Tailwind utility class) while staying inside this plan's exclusive file set.

## Issues Encountered

- `frontend/node_modules` did not exist in this fresh worktree (Plan 03's `npm install` output wasn't part of any commit, as expected for a build artifact) — ran `npm install` from the committed `package.json`/`package-lock.json`, which installed cleanly with the exact pinned versions including `lightweight-charts@5.2.0`. No new dependency was added.
- `npm run build` hit the same sandbox `EROFS` restriction documented in `01-03-SUMMARY.md` (Next's internal TypeScript-config-validation step tries to write to the shared `~/.npm/_cacache`, which was already at `up to date` and only fails when the sandbox denies write access to that path). Retried with the sandbox override — not a code defect, matches the prior plan's documented environment issue.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The watchlist panel is fully live and ready for full-stack manual verification (10 seeded tickers streaming, add/remove, inline errors) once the backend (Plan 01/02/04) is running on `:8000` alongside `npm run dev`
- `SelectedTickerContext.setSelected` is now actually driven by row clicks — Plan 06 (main chart) can read `useSelectedTicker().selected` and render against it without any further wiring on this side
- `frontend/lib/*` remains completely untouched by this plan, confirmed via `git diff --stat` against the wave's base commit

## Self-Check: PASSED

- FOUND: frontend/components/Sparkline.tsx
- FOUND: frontend/components/WatchlistRow.tsx
- FOUND: frontend/components/AddTickerInput.tsx
- FOUND: frontend/components/WatchlistPanel.tsx
- FOUND: commit a7cf960
- FOUND: commit fa8415c

---
*Phase: 01-live-market-terminal*
*Completed: 2026-07-14*
