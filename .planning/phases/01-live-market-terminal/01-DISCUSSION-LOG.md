# Phase 1: Live Market Terminal - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-14
**Phase:** 1-Live Market Terminal
**Areas discussed:** Charting library, Watchlist add/remove UX, Phase 1 layout shell

---

## Charting Library

| Option | Description | Selected |
|--------|-------------|----------|
| Lightweight Charts (both) | Canvas, finance-grade, ~45KB; one library for sparklines + main chart; best streaming perf | ✓ |
| Lightweight main + custom sparklines | Lightweight for big chart; hand-rolled canvas/SVG sparklines per row | |
| Recharts (both) | SVG/React declarative; easier to theme, heavier, less ideal for many live series | |

**User's choice:** Lightweight Charts for both surfaces.
**Notes:** Aligns with PLAN.md §10 "canvas-based charting library preferred." Drives sparklines and the main detail chart; both backfill from `/api/prices/{ticker}/history` then extend via SSE.

---

## Watchlist Add/Remove UX

| Option | Description | Selected |
|--------|-------------|----------|
| Inline input + hover-remove | Always-visible ticker input (type + Enter); row reveals '×' on hover | ✓ |
| '+' button + add field | '+' reveals an add field; persistent '×' or context menu to remove | |
| Add field + confirm remove | Inline add, but removal asks for a small confirm | |

**User's choice:** Inline input + hover-revealed '×'.
**Notes:** Fast, dense, terminal-like; no modal. Server-side validation surfaces errors inline; duplicate adds idempotent.

---

## Phase 1 Layout Shell

| Option | Description | Selected |
|--------|-------------|----------|
| Full grid + placeholders | Build final multi-panel Bloomberg grid now with empty placeholders for later phases | ✓ |
| Watchlist + chart only | Build only Phase 1 needs; restructure into full grid later | |
| Sidebar + main, grows later | Watchlist left sidebar, chart center; add regions around it later | |

**User's choice:** Full grid now with empty placeholder panels for portfolio/positions/chat.
**Notes:** Later phases fill panels without relayout. Header connection-status dot is real in Phase 1; portfolio/cash figures are stubs until Phase 2.

---

## Claude's Discretion

- **Chart default + style** (offered but not selected for discussion): auto-select first watchlist ticker on load; main chart = filled-area line; sparklines = minimal direction-colored lines. Revisitable in `/gsd-ui-phase 1`.
- Grid proportions, spacing, placeholder styling, and price-flash animation timing — per PLAN.md §2/§10 aesthetic and the UI design contract.
- Exact Next.js scaffolding / dev-proxy setup — planner/researcher own it.

## Deferred Ideas

- Trading, positions, live header financials → Phase 2.
- Portfolio heatmap + P&L chart → Phase 3.
- AI copilot chat → Phase 4.
- (Placeholder panels only in Phase 1; no behavior.)
