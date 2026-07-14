---
status: testing
phase: 01-live-market-terminal
source: [01-VERIFICATION.md]
started: 2026-07-14T22:13:13Z
updated: 2026-07-14T22:13:13Z
---

## Current Test

number: 1
name: Watchlist live flash + populated sparklines
expected: |
  10 seeded ticker rows are visible, each price briefly flashes green (uptick) or
  red (downtick) and fades to transparent over ~500ms; sparklines are visibly
  populated (not blank) on first paint and grow over time.
awaiting: user response

## Tests

### 1. Watchlist live flash + populated sparklines
expected: Open http://localhost:8000 with the backend running; watch the watchlist for ~10-15 seconds. 10 seeded ticker rows visible; each price briefly flashes green (uptick) / red (downtick) and fades to transparent over ~500ms; sparklines populated on first paint and grow over time.
result: [pending]

### 2. Ticker selection swaps the main chart
expected: Click a different watchlist row. The chart briefly shows "Loading chart…" (or swaps instantly if backfill is cached), then renders a populated filled-area chart for the newly selected ticker, growing live afterward; header symbol/price/change% updates to match.
result: [pending]

### 3. Tablet-width layout remains usable
expected: Resize the browser to tablet width (~768-1024px). Per UI-09 "functional on tablet", panels reflow/stack without being cut off or unusable; the AI-chat rail (hidden below `xl`) does not leave dead space.
result: [pending]

### 4. Inline validation error on invalid ticker
expected: Add an invalid ticker (e.g. "12345" or a 6+ letter string) via the watchlist input. An inline red error message appears directly beneath the input with the server's detail message — no toast/modal — and the field is not cleared.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
