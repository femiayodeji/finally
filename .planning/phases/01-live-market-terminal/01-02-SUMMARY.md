---
phase: 01-live-market-terminal
plan: 02
subsystem: market-data
tags: [python, dataclasses, deque, price-cache, sse]

# Dependency graph
requires: []
provides:
  - "PriceUpdate.session_reference field + session_change_percent computed property"
  - "PriceCache session reference capture per ticker (stable for process lifetime)"
  - "PriceCache bounded ~600-point rolling per-ticker price history ring buffer"
  - "PriceCache.get_history(ticker) -> list[{timestamp, price}]"
affects: [live-market-terminal, portfolio-apis, frontend-watchlist, frontend-charts]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive dataclass field extension (default None) to preserve backward compatibility on a frozen/slots dataclass"
    - "collections.deque(maxlen=N) as a bounded FIFO ring buffer under an existing threading.Lock"
    - "dict.setdefault() for once-only capture semantics (session reference)"

key-files:
  created: []
  modified:
    - backend/app/market/models.py
    - backend/app/market/cache.py
    - backend/tests/market/test_models.py
    - backend/tests/market/test_cache.py

key-decisions:
  - "session_reference defaults to None on PriceUpdate and session_change_percent falls back to price when None, so a bare/first-tick PriceUpdate reports 0% session change without requiring callers to pass a reference"
  - "History ring buffer capacity is a module constant (MAX_HISTORY_POINTS = 600) in cache.py rather than a PriceCache constructor parameter, mirroring the existing module-constant style (PLAN.md §6 sizing: ~600 points at 500ms cadence)"
  - "get_history returns a defensive list copy (not the live deque) so external callers cannot mutate cache-internal state (T-02-02 mitigation)"

patterns-established:
  - "Bounded per-ticker in-memory history via maxlen deque, mirrored by remove() cleanup across all three per-ticker structures (_prices, _session_refs, _history)"

requirements-completed: [MKT-01, MKT-02, MKT-03]

coverage:
  - id: D1
    description: "PriceUpdate carries an optional session_reference and computes session_change_percent (latest vs session reference), included in to_dict() as a strict superset of prior keys"
    requirement: "MKT-03"
    verification:
      - kind: unit
        ref: "backend/tests/market/test_models.py::TestPriceUpdate::test_session_change_percent_positive"
        status: pass
      - kind: unit
        ref: "backend/tests/market/test_models.py::TestPriceUpdate::test_session_change_percent_negative"
        status: pass
      - kind: unit
        ref: "backend/tests/market/test_models.py::TestPriceUpdate::test_session_change_percent_first_tick_zero"
        status: pass
      - kind: unit
        ref: "backend/tests/market/test_models.py::TestPriceUpdate::test_to_dict_includes_session_change_percent"
        status: pass
    human_judgment: false
  - id: D2
    description: "PriceCache captures a per-ticker session reference price once (on first observation) and never overwrites it for the process lifetime"
    requirement: "MKT-01"
    verification:
      - kind: unit
        ref: "backend/tests/market/test_cache.py::TestPriceCache::test_session_reference_captured_on_first_update"
        status: pass
      - kind: unit
        ref: "backend/tests/market/test_cache.py::TestPriceCache::test_session_reference_stable_across_updates"
        status: pass
      - kind: unit
        ref: "backend/tests/market/test_cache.py::TestPriceCache::test_session_change_percent_threaded_through_update"
        status: pass
    human_judgment: false
  - id: D3
    description: "PriceCache maintains a bounded ~600-point per-ticker rolling price history ring buffer with FIFO eviction, exposed via get_history(), and remove() clears price/session-reference/history together"
    requirement: "MKT-02"
    verification:
      - kind: unit
        ref: "backend/tests/market/test_cache.py::TestPriceCache::test_history_grows_with_updates"
        status: pass
      - kind: unit
        ref: "backend/tests/market/test_cache.py::TestPriceCache::test_history_bounded_with_fifo_eviction"
        status: pass
      - kind: unit
        ref: "backend/tests/market/test_cache.py::TestPriceCache::test_get_history_unknown_ticker"
        status: pass
      - kind: unit
        ref: "backend/tests/market/test_cache.py::TestPriceCache::test_get_history_returns_copy"
        status: pass
      - kind: unit
        ref: "backend/tests/market/test_cache.py::TestPriceCache::test_remove_clears_session_reference_and_history"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-14
status: complete
---

# Phase 1 Plan 2: Session Reference & Rolling History Summary

**Additively extended `PriceUpdate`/`PriceCache` with a server-computed `session_change_percent` and a bounded ~600-point per-ticker price history ring buffer, keeping the already-built market-data subsystem's public surface unchanged.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-14T22:00Z (approx.)
- **Completed:** 2026-07-14T22:16:17+01:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `PriceUpdate` gained an optional `session_reference` field and a `session_change_percent` computed property (latest vs. session-open price), with `to_dict()` extended as a strict superset of the prior payload
- `PriceCache` now captures each ticker's session reference price once (first observation after process start) and threads it into every constructed `PriceUpdate`
- `PriceCache` maintains a bounded (`MAX_HISTORY_POINTS = 600`) per-ticker rolling history ring buffer (`collections.deque(maxlen=600)`) with FIFO eviction, exposed via `get_history(ticker) -> list[{timestamp, price}]`
- `remove()` now clears a ticker's price, session reference, and history together, so re-adding a ticker starts a fresh session

## Task Commits

Each task was committed atomically:

1. **Task 1: Session reference price + session_change_percent on PriceUpdate** - `1f1b013` (feat)
2. **Task 2: Session reference capture + rolling history ring buffer in PriceCache** - `48d0e30` (feat)

**Plan metadata:** (this commit, following SUMMARY.md creation)

_Note: implementation and tests were written together per task and verified green before commit; both task commits include their corresponding test file changes rather than separate RED/GREEN commits, since this is an additive extension to an already-passing, already-tested module (no failing-test phase was meaningful to capture separately)._

## Files Created/Modified
- `backend/app/market/models.py` - Added `session_reference` field and `session_change_percent` property to `PriceUpdate`; extended `to_dict()`
- `backend/app/market/cache.py` - Added `_session_refs`/`_history` dicts, session capture + history append in `update()`, new `get_history()`, extended `remove()`; added module constant `MAX_HISTORY_POINTS = 600`
- `backend/tests/market/test_models.py` - Added 5 tests for `session_change_percent` (positive, negative, first-tick-zero, zero-reference, `to_dict()` superset)
- `backend/tests/market/test_cache.py` - Added 8 tests for session-reference capture/stability, history growth/bound/FIFO eviction, `get_history` known/unknown, and `remove()` clearing all three structures

## Decisions Made
- `session_reference` defaults to `None` and `session_change_percent` falls back to `price` as the reference when `None`, so a bare `PriceUpdate` (e.g. constructed without going through `PriceCache`) still reports 0% session change rather than raising or requiring every caller to pass a reference
- History buffer cap (`MAX_HISTORY_POINTS`) is a module-level constant in `cache.py`, matching the existing convention of module-level constants (e.g. `TRADING_SECONDS_PER_YEAR` in `simulator.py`) rather than a per-instance constructor parameter — no plan or caller needs a non-default cap yet
- `get_history()` returns a list copy of the deque contents (not the deque itself) so callers cannot mutate cache-internal state, satisfying threat T-02-02 (Tampering — shared cache mutation)

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria met:
- `to_dict()` emits `session_change_percent` and every pre-existing key (verified by test)
- `session_change_percent` is `0.0` on the first observation (reference == price)
- Existing `change`/`change_percent`/`direction` semantics unchanged (all 24 pre-existing model+cache tests still pass unmodified)
- Session reference is set once per ticker and unchanged by later updates
- History is bounded at 600 points with FIFO eviction (verified by pushing 650 updates and asserting length + oldest/newest timestamps)
- `get_history` returns `[{timestamp, price}]` for known tickers and `[]` for unknown tickers
- `remove()` clears price, session reference, and history for the ticker
- Full market suite (73 existing + 13 new = 86 tests) passes; `ruff check app/ tests/` is clean

## Issues Encountered
- The sandboxed `uv` cache directory (`~/.cache/uv`) is read-only under default sandbox restrictions, causing `uv run` to fail with "Could not acquire lock ... Read-only file system". Test/lint commands were re-run with the sandbox override for this project-local, read-only-safe build/test tooling only (no destructive or network operations involved) — this is an environment limitation, not a plan deviation.

## User Setup Required

None - no external service configuration required. Changes are self-contained to the existing market-data subsystem.

## Next Phase Readiness
- `backend/app/market/cache.py` now exposes everything `GET /api/prices/{ticker}/history` (a separate, not-yet-built API route in this phase) needs to backfill charts/sparklines
- SSE payloads emitted via `PriceUpdate.to_dict()` (used by `stream.py`, unmodified) now include `session_change_percent` automatically once the market-data background task calls `PriceCache.update()` — no changes needed in `stream.py` itself
- No blockers for downstream plans in this phase (API routes, frontend wiring) that consume this cache/model surface

---
*Phase: 01-live-market-terminal*
*Completed: 2026-07-14*
