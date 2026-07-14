---
phase: 01-live-market-terminal
plan: 03
subsystem: ui
tags: [nextjs, react, typescript, tailwind, static-export, terminal-shell]

# Dependency graph
requires:
  - phase: 01-live-market-terminal
    provides: "frontend/lib/* data-layer contracts (PriceStreamContext, WatchlistContext, PortfolioContext, api, format, types, usePriceHistory) — existing, untracked-until-this-plan"
provides:
  - "Next.js App-Router TypeScript project scaffolded in frontend/ with static export (output:'export')"
  - "Tailwind dark theme with all locked UI-SPEC color tokens plus up/down/ink-dim aliases required by lib/format.ts"
  - "Dev-mode /api/* rewrite proxy to :8000"
  - "Terminal grid shell: Header with live ConnectionDot + TOTAL VALUE/CASH stubs, 320px watchlist column, main-chart-over-3-up-placeholder center column, 340px AI-chat rail"
  - "SelectedTickerContext — the seam letting Plan 05 (watchlist) and Plan 06 (chart) ship in parallel"
  - "frontend/lib/* contracts committed to git for the first time (previously untracked due to a gitignore rule collision)"
affects: [01-04, 01-05, 01-06]

# Tech tracking
tech-stack:
  added: [next@16.2.10, react@19.2.7, react-dom@19.2.7, typescript@7.0.2, tailwindcss@3.4.19, postcss@8.5.19, autoprefixer@10.5.3, lightweight-charts@5.2.0]
  patterns:
    - "Panel.tsx as the shared bg-panel/border-muted/6px-radius/16px-padding wrapper every panel composes"
    - "Placeholder components (WatchlistPanel, MainChartPanel, PlaceholderPanel) that later plans replace the body of without touching layout.tsx/page.tsx"
    - "Providers mounted once at root (layout.tsx): PriceStreamProvider -> WatchlistProvider -> SelectedTickerProvider"

key-files:
  created:
    - frontend/package.json
    - frontend/tsconfig.json
    - frontend/next.config.ts
    - frontend/postcss.config.mjs
    - frontend/tailwind.config.ts
    - frontend/app/globals.css
    - frontend/app/layout.tsx
    - frontend/app/page.tsx
    - frontend/components/Panel.tsx
    - frontend/components/Header.tsx
    - frontend/components/ConnectionDot.tsx
    - frontend/components/WatchlistPanel.tsx
    - frontend/components/MainChartPanel.tsx
    - frontend/components/PlaceholderPanel.tsx
    - frontend/lib/SelectedTickerContext.tsx
  modified:
    - .gitignore

key-decisions:
  - "Narrowed the root .gitignore's bare `lib/` rule to `backend/lib/` so frontend/lib/* is committable while still excluding Python venv/build lib dirs"
  - "Set next.config.ts typescript.ignoreBuildErrors and moved type-checking to a standalone `tsc --noEmit` pre-build step, working around a Next 16.2.10 / typescript@7.0.2 integration bug in Next's internal type-check worker"
  - "AI-chat rail collapses via a pure CSS `hidden xl:block` breakpoint rather than an interactive JS toggle — sufficient for Phase 1's non-interactive placeholder scope; a manual toggle button can be added when the panel becomes interactive in Phase 4"

patterns-established:
  - "Pattern: thin placeholder components (WatchlistPanel, MainChartPanel) are standalone files from day one so future plans replace only their body, never layout.tsx/page.tsx"
  - "Pattern: contexts under frontend/lib follow the existing PriceStreamContext/WatchlistContext shape (createContext + Provider + use-hook, 'use client' at top)"

requirements-completed: [UI-09, APP-02]

coverage:
  - id: D1
    description: "npm run build produces a static export in frontend/out with output:'export'"
    requirement: "APP-02"
    verification:
      - kind: other
        ref: "cd frontend && npm run build && test -f out/index.html"
        status: pass
    human_judgment: false
  - id: D2
    description: "Tailwind dark theme defines all locked UI-SPEC tokens including up/down/ink-dim aliases lib/format.ts depends on"
    requirement: "UI-09"
    verification:
      - kind: other
        ref: "grep generated CSS in frontend/out for .bg-canvas/.text-accent-yellow/.bg-positive/.text-up/.text-down/.text-ink-dim rules — all resolve to locked hex values"
        status: pass
    human_judgment: false
  - id: D3
    description: "Terminal grid shell renders header, watchlist column, main-chart+3-up center column, AI-chat rail with correct placeholder copy"
    requirement: "UI-09"
    verification:
      - kind: other
        ref: "grep frontend/out/index.html for 'FinAlly', 'AI Assistant', 'No positions yet', 'Portfolio heatmap', 'Performance chart' — all present"
        status: pass
    human_judgment: true
    rationale: "Visual layout correctness (proportions, spacing, dark theme fidelity) requires a human to view the rendered page; static export text-content grep confirms copy and CSS confirms tokens, but not visual composition."
  - id: D4
    description: "Header connection dot is live, driven by PriceStreamContext.status"
    requirement: "UI-09"
    verification:
      - kind: other
        ref: "ConnectionDot reads usePriceStream().status via the STATE_META lookup (connected/reconnecting/disconnected) — no independent state or polling"
        status: pass
    human_judgment: true
    rationale: "Confirming the dot actually flips color live requires running the backend SSE stream and observing the browser — deferred to manual full-stack verification noted below."

# Metrics
duration: 20min
completed: 2026-07-14
status: complete
---

# Phase 1 Plan 03: Next.js Scaffold & Terminal Shell Summary

**Next.js 16 + TypeScript 7 static-export app scaffolded with a locked Tailwind dark theme, and the Bloomberg-style terminal grid shell (header, watchlist column, chart+3-up center, AI-chat rail) wired to a live connection dot and placeholder panels.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-14T22:24:00Z (worktree spawn)
- **Completed:** 2026-07-14T22:38:06Z
- **Tasks:** 2 (plus 1 pre-resolved checkpoint)
- **Files modified:** 16 (7 copied contract files, 1 gitignore, 8 new scaffold/shell files)

## Accomplishments
- Scaffolded a Next.js App-Router TypeScript project (`frontend/`) with static export (`output: 'export'`), a dev-mode `/api/*` rewrite proxy to `:8000`, and strict TypeScript with a `@/*` path alias
- Built a Tailwind v3 dark theme with every locked color token from 01-UI-SPEC.md (`canvas`, `panel`, `border-muted`, `accent-blue`, `accent-yellow`, `accent-purple`, `positive`, `negative`, `neutral`) plus the `up`/`down`/`ink-dim` aliases `frontend/lib/format.ts` depends on — verified present in the compiled CSS with correct hex values
- Built the full terminal grid shell: 56px header with a yellow "FinAlly" wordmark, a live `ConnectionDot` reading `PriceStreamContext.status`, and em-dash TOTAL VALUE/CASH stubs (never `$0.00`); a 320px watchlist column; a center column with the main chart panel (~60%) over a 3-up Heatmap/Positions/P&L placeholder row (~40%); a 340px AI-chat rail (collapses below the `xl` breakpoint) with a grayed, non-focusable input preview
- Added `SelectedTickerContext` — the shared-state seam that lets Plan 05 (watchlist row click) and Plan 06 (chart render) ship as parallel plans without either editing the other's files
- Recovered the `frontend/lib/*` data-layer contracts (7 files) into git for the first time — they existed only as untracked files in history because the root `.gitignore`'s Python-oriented `lib/` rule also matched `frontend/lib/`

## Task Commits

Each task was committed atomically:

1. **Deviation baseline: copy locked frontend/lib contracts, narrow gitignore** - `7313a1b` (chore)
2. **Task 1: Next.js scaffold, static export, Tailwind dark theme, dev API proxy** - `1f9c6da` (feat)
3. **Task 2: terminal grid shell, live connection dot, placeholder panels** - `74f2adb` (feat)

_No TDD tasks in this plan._

## Files Created/Modified
- `frontend/package.json` - pinned dependencies (checkpoint-approved exact versions), dev/build/start/lint scripts
- `frontend/tsconfig.json` - strict TS, `moduleResolution: bundler`, `@/*` alias (no `baseUrl` — removed by TS7)
- `frontend/next.config.ts` - `output: 'export'`, `images.unoptimized`, dev `/api/*` rewrite, `typescript.ignoreBuildErrors` (see Deviations)
- `frontend/postcss.config.mjs` - tailwindcss + autoprefixer
- `frontend/tailwind.config.ts` - locked color tokens + up/down/ink-dim aliases, Inter font family, `rounded-panel` (6px)
- `frontend/app/globals.css` - Tailwind directives, canvas background, Inter font var, `.numeric` (tabular-nums) utility
- `frontend/app/layout.tsx` - root layout mounting `PriceStreamProvider` → `WatchlistProvider` → `SelectedTickerProvider`, Inter font
- `frontend/app/page.tsx` - composes the full terminal grid
- `frontend/components/Panel.tsx` - shared panel chrome wrapper
- `frontend/components/Header.tsx` - 56px header bar, wordmark, connection status, stub figures
- `frontend/components/ConnectionDot.tsx` - live 8px status dot
- `frontend/components/WatchlistPanel.tsx` - thin placeholder (Plan 05 replaces body)
- `frontend/components/MainChartPanel.tsx` - thin placeholder (Plan 06 replaces body)
- `frontend/components/PlaceholderPanel.tsx` - shared empty-state used by Heatmap/Positions/P&L/AI Assistant
- `frontend/lib/SelectedTickerContext.tsx` - shared selected-ticker state
- `frontend/lib/{PriceStreamContext,WatchlistContext,PortfolioContext,api,format,types,usePriceHistory}.{ts,tsx}` - copied verbatim from the main checkout (pre-existing contracts, not authored by this plan)
- `.gitignore` - narrowed `lib/` → `backend/lib/`; added a frontend/Node section (`node_modules/`, `frontend/.next/`, `frontend/out/`, `frontend/next-env.d.ts`, `*.tsbuildinfo`)

## Decisions Made
- Pinned exact versions per the pre-resolved package-legitimacy checkpoint (next 16.2.10, react/react-dom 19.2.7, typescript 7.0.2, tailwindcss 3.4.19 v3-style, lightweight-charts 5.2.0) — no wildcard ranges
- Chose `backend/lib/` (rather than deleting the rule or scoping to `/lib/`) to narrow the gitignore collision, since Python build artifacts under this repo only ever live inside `backend/`
- Implemented the AI-chat rail's tablet "collapse" purely via a CSS breakpoint (`hidden xl:block`) rather than building an interactive JS toggle button — the panel is non-interactive placeholder content this phase (Phase 4 wires the real chat), so a manual toggle affordance would be premature; can be added when the panel becomes interactive

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] frontend/lib/* contracts existed only as untracked files, unreachable from a fresh worktree**
- **Found during:** Pre-execution (worktree had no `frontend/` directory at all — confirmed via `ls`)
- **Issue:** The plan's `<context>` block references `frontend/lib/{PriceStreamContext,WatchlistContext,api,format,types}.tsx` as existing, locked contract files. They exist in the main checkout's working tree but were never committed, because the root `.gitignore`'s bare `lib/` rule (written for Python's `venv/lib/`) also matches `frontend/lib/` anywhere in the tree. A worktree built from git history therefore has no `frontend/` directory at all.
- **Fix:** Copied all 7 files verbatim from the main checkout into this worktree's `frontend/lib/`, then narrowed the gitignore rule from `lib/` to `backend/lib/` so the copies (and all future frontend/lib files) are committable. This exact remediation was pre-approved in the checkpoint instructions.
- **Files modified:** `.gitignore`, `frontend/lib/PriceStreamContext.tsx`, `frontend/lib/WatchlistContext.tsx`, `frontend/lib/PortfolioContext.tsx`, `frontend/lib/api.ts`, `frontend/lib/format.ts`, `frontend/lib/types.ts`, `frontend/lib/usePriceHistory.ts`
- **Verification:** `diff -r` against the main checkout's `frontend/lib/` confirmed byte-identical copies; `git add --dry-run frontend/` confirmed `node_modules`/`.next`/`out` remain excluded after the gitignore edit
- **Committed in:** `7313a1b`

**2. [Rule 1 - Bug] Removed `baseUrl` from tsconfig.json — TS 7.0.2 removed the option**
- **Found during:** Task 1 (`npm run build` verification)
- **Issue:** `typescript@7.0.2` throws `TS5102: Option 'baseUrl' has been removed` — a breaking change from the TS5/6 config surface this plan's action text assumed
- **Fix:** Removed `baseUrl` from `tsconfig.json`; the `@/*` path alias continues to resolve correctly (TS 4.1+ resolves non-relative `paths` against the tsconfig directory when `baseUrl` is absent)
- **Files modified:** `frontend/tsconfig.json`
- **Verification:** `tsc --noEmit` passes clean; `@/lib/...` and `@/components/...` imports resolve in the build
- **Committed in:** `1f9c6da`

**3. [Rule 1 - Bug] Worked around a Next 16.2.10 / TypeScript 7.0.2 integration bug in Next's internal type-check worker**
- **Found during:** Task 1 (`npm run build` verification)
- **Issue:** After fixing `baseUrl`, `next build`'s internal "Running TypeScript" step still crashed with `The "id" argument must be of type string. Received undefined`, and separately printed a false "TypeScript... required package(s) not installed" message despite `typescript@7.0.2` being present — an integration bug between Next's bundled type-check worker and the newer TS7 compiler API surface, not a real type error (confirmed: standalone `tsc --noEmit` passes clean)
- **Fix:** Set `typescript: { ignoreBuildErrors: true }` in `next.config.ts` (with an inline comment explaining why) and changed the `build` script to `tsc --noEmit && next build`, so a genuine type error still fails the build via the working standalone compiler, while Next's broken internal check is bypassed
- **Files modified:** `frontend/next.config.ts`, `frontend/package.json`
- **Verification:** `npm run build` completes successfully from a clean `.next`/`out`; `tsc --noEmit` (run standalone and as the pre-build step) exits 0
- **Committed in:** `1f9c6da`

**4. [Rule 2 - Missing Critical] Added a frontend/Node section to .gitignore**
- **Found during:** Task 1 (before first `git add`)
- **Issue:** The root `.gitignore` was entirely Python-oriented with no `node_modules/`, `.next/`, `out/`, or `next-env.d.ts` entries — without this, a `git add frontend/` would have picked up the ~100MB `node_modules/` tree and build output
- **Fix:** Added a dedicated frontend/Node section excluding `node_modules/`, `frontend/.next/`, `frontend/out/`, `frontend/next-env.d.ts`, `*.tsbuildinfo`
- **Files modified:** `.gitignore`
- **Verification:** `git add --dry-run frontend/` lists only source files (16 files), no `node_modules`/build artifacts
- **Committed in:** `7313a1b`

---

**Total deviations:** 4 auto-fixed (1 Rule 3 blocking, 2 Rule 1 bugs, 1 Rule 2 missing-critical)
**Impact on plan:** All four were necessary to make the plan's own verification command (`npm run build && test -f out/index.html`) pass at all, given a genuinely fresh worktree and the newer TS7/Next16 pairing. No scope creep — no new features, no architectural changes.

## Issues Encountered
- `npm install` initially failed with `EROFS` writing to the shared `~/.npm/_cacache` — a sandbox filesystem restriction on the npm cache directory, not a package problem. Re-ran with the sandbox override; installed cleanly with the exact pinned versions.
- `npm audit` reports 2 moderate vulnerabilities in a transitive `postcss` version bundled *inside* `next@16.2.10`'s own `node_modules/next/node_modules/postcss` (XSS via unescaped `</style>` in CSS stringify output, GHSA-qx2v-qp2m-jg93). No fix is available upstream at this `next` version, and it's unrelated to this project's own pinned `postcss@8.5.19`. Not auto-fixed (would require an unapproved `next` version change); flagged here for awareness, not blocking.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `frontend/` is a working Next.js project; `npm run build` and (once the backend is running) `npm run dev` both function
- `WatchlistPanel` and `MainChartPanel` are ready for Plans 05/06 to fill in without touching `layout.tsx`/`page.tsx`
- `SelectedTickerContext` is mounted and ready for the watchlist-click → chart-render wiring
- Full-stack manual verification (dot turning green against a live backend SSE stream) was not performed in this plan — requires the backend (Plan 01/02) running on `:8000`; noted as the plan's own "Manual (full stack)" verification step, deferred to whenever both sides are up together
- Known, non-blocking: `next@16.2.10`'s bundled `postcss` has an upstream moderate-severity advisory with no fix yet (see Issues Encountered)

## Self-Check: PASSED

- FOUND: frontend/package.json
- FOUND: frontend/tsconfig.json
- FOUND: frontend/next.config.ts
- FOUND: frontend/postcss.config.mjs
- FOUND: frontend/tailwind.config.ts
- FOUND: frontend/app/globals.css
- FOUND: frontend/app/layout.tsx
- FOUND: frontend/app/page.tsx
- FOUND: frontend/components/Panel.tsx
- FOUND: frontend/components/Header.tsx
- FOUND: frontend/components/ConnectionDot.tsx
- FOUND: frontend/components/WatchlistPanel.tsx
- FOUND: frontend/components/MainChartPanel.tsx
- FOUND: frontend/components/PlaceholderPanel.tsx
- FOUND: frontend/lib/SelectedTickerContext.tsx
- FOUND: commit 7313a1b
- FOUND: commit 1f9c6da
- FOUND: commit 74f2adb

---
*Phase: 01-live-market-terminal*
*Completed: 2026-07-14*
