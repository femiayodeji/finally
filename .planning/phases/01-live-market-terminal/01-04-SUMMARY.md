---
phase: 01-live-market-terminal
plan: 04
subsystem: api
tags: [fastapi, sqlite, watchlist, prices, rest]

# Dependency graph
requires:
  - "backend/app/db/database.py get_connection()/DEFAULT_USER_ID (01-01)"
  - "backend/app/main.py create_app() composition root + router registration site (01-01)"
  - "backend/app/market/cache.py PriceCache.get_history()/session_change_percent (01-02)"
provides:
  - "GET /api/prices/{ticker}/history — chart/sparkline backfill"
  - "GET/POST/DELETE /api/watchlist — full watchlist CRUD (WATCH-01..04)"
  - "app/services/watchlist_service.py — validation + tracked-set orchestration"
  - "app/db/watchlist_repo.py — watchlist table CRUD + has_open_position()"
affects: [01-03, 01-05, 01-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Router factory closes over PriceCache (created before lifespan); mutating watchlist routes read request.app.state.market_source at request time since the market source is only constructed inside the lifespan"
    - "isinstance(source, SimulatorDataSource) branches Massive-mode-only unpriceable-symbol rejection/rollback logic"

key-files:
  created:
    - backend/app/db/watchlist_repo.py
    - backend/app/services/__init__.py
    - backend/app/services/watchlist_service.py
    - backend/app/api/prices.py
    - backend/app/api/watchlist.py
    - backend/tests/api/test_prices.py
  modified:
    - backend/app/api/__init__.py
    - backend/app/main.py
    - backend/tests/api/test_watchlist.py

key-decisions:
  - "Watchlist router's POST/DELETE handlers read the market source via request.app.state.market_source rather than a closure argument — the plan's literal 'passing app.state.cache and app.state.source' phrasing doesn't hold because the source object doesn't exist until the lifespan runs (it needs db.initialize() + get_tracked_tickers() first, per APP-03 order), while router registration happens before that, at create_app() time"
  - "Massive-mode unpriceable-symbol rejection uses isinstance(source, SimulatorDataSource) to skip the poll-and-rollback branch for the simulator (which seeds the cache synchronously) — keeps the tested default path fast and deterministic while still implementing the Massive-mode contract"
  - "watchlist route tests were split: repo/service unit tests + earlier route tests both live in tests/api/test_watchlist.py (Task 1 wrote the unit tests; Task 2 appended the TestClient route tests once the router existed), matching the plan's top-level files_modified list"

requirements-completed: [MKT-04, MKT-05, WATCH-01, WATCH-02, WATCH-03, WATCH-04, APP-01]

coverage:
  - id: D1
    description: "GET /api/prices/{ticker}/history returns {ticker, history:[{timestamp,price}]}; empty list (200, not 404) for an untracked ticker; path param uppercased"
    requirement: "MKT-04"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_prices.py::TestPriceHistoryRoute"
        status: pass
      - kind: manual_procedural
        ref: "curl localhost:8321/api/prices/AAPL/history returned 5 populated {timestamp,price} points"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /api/watchlist returns the seeded tickers each with a WatchlistEntry price snapshot including session_change_percent"
    requirement: "WATCH-01"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_watchlist.py::TestWatchlistRoutes::test_get_watchlist_returns_seeded_tickers, TestListWatchlist"
        status: pass
      - kind: manual_procedural
        ref: "curl localhost:8321/api/watchlist returned 10 tickers with price/session_change_percent populated"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /api/watchlist validates (uppercase, 1-5 letters), is idempotent on duplicates, and starts tracking the ticker via source.add_ticker"
    requirement: "WATCH-02, WATCH-03"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_watchlist.py::TestServiceAdd, TestWatchlistRepoIdempotency, TestWatchlistRoutes::test_post_adds_valid_ticker, test_post_invalid_symbol_returns_400_with_detail"
        status: pass
      - kind: manual_procedural
        ref: "curl -XPOST localhost:8321/api/watchlist -d '{\"ticker\":\"pypl\"}' returned {\"ticker\":\"PYPL\"}"
        status: pass
    human_judgment: false
  - id: D4
    description: "DELETE /api/watchlist/{ticker} removes the DB row but keeps price tracking (does not call source.remove_ticker) while an open position remains"
    requirement: "WATCH-04, MKT-05"
    verification:
      - kind: unit
        ref: "backend/tests/api/test_watchlist.py::TestServiceRemove::test_remove_keeps_tracking_when_position_open, test_remove_untracks_when_no_open_position; TestWatchlistRoutes::test_delete_removes_ticker"
        status: pass
    human_judgment: false
  - id: D5
    description: "Both routers registered in main.py at the documented site without disturbing health/stream/static; full backend suite green"
    requirement: "APP-01"
    verification:
      - kind: unit
        ref: "backend/tests/api/ — 29 tests pass; full suite 123 tests pass"
        status: pass
      - kind: manual_procedural
        ref: "ruff check app/ tests/ — All checks passed; live uvicorn smoke test — /api/watchlist, POST, /api/prices/AAPL/history all responded correctly"
        status: pass
    human_judgment: false
---

# Phase 1 Plan 4: Prices History + Watchlist CRUD API Summary

**`GET /api/prices/{ticker}/history` for chart/sparkline backfill and full `GET/POST/DELETE /api/watchlist` CRUD, both registered in `app/main.py`, enforcing server-side symbol validation and the watchlist-∪-open-positions tracked-set rule.**

## Performance

- **Duration:** ~2 min (task-commit timestamps)
- **Started:** 2026-07-14T21:50:48Z (approx, first commit)
- **Completed:** 2026-07-14T21:52:48Z
- **Tasks:** 2
- **Files modified:** 9 (6 created, 3 modified)

## Accomplishments

- `backend/app/db/watchlist_repo.py`: `list_tickers()`, `add_ticker()` (idempotent `INSERT OR IGNORE`, WATCH-02), `remove_ticker()`, `has_open_position()` (checks the `positions` table, empty this phase but query exists for MKT-05)
- `backend/app/services/watchlist_service.py`: `validate_symbol()` (uppercase, 1-5 ASCII letters, T-04-01), `list_watchlist(cache)` (merges DB tickers with `PriceCache` snapshots into the exact `WatchlistEntry` shape from `frontend/lib/types.ts`, nulls before first tick), `add(cache, source, ticker)` and `remove(cache, source, ticker)` — the async orchestration that keeps the DB and the market source's tracked set in sync
- Simulator mode (default, tested): any well-formed symbol is accepted immediately — `SimulatorDataSource.add_ticker()` seeds the cache synchronously. Massive mode: `add()` gives the poller a brief bounded window (`isinstance(source, SimulatorDataSource)` gate) to resolve a price, rolling back the DB row and tracking if it never does (WATCH-03)
- `backend/app/api/prices.py`: `GET /api/prices/{ticker}/history` → `{ticker, history: cache.get_history(TICKER)}`, empty list (200) for an untracked ticker (MKT-04)
- `backend/app/api/watchlist.py`: `GET /api/watchlist`, `POST /api/watchlist` (`{ticker}` → `{ticker}` or 400 `{detail}`), `DELETE /api/watchlist/{ticker}` (WATCH-01/02/03/04)
- `backend/app/main.py`: both routers registered at the documented site; health/stream/static routing untouched
- 29 new tests (17 repo/service unit + 3 prices route + 9 watchlist route); full backend suite grew from 86 to 123 tests, all green; `ruff check app/ tests/` clean
- Manually verified end-to-end against a live `uvicorn` process: `GET /api/watchlist` listed the 10 seeded tickers with prices, `POST /api/watchlist {"ticker":"pypl"}` returned `{"ticker":"PYPL"}`, `GET /api/prices/AAPL/history` returned populated `{timestamp,price}` points

## Task Commits

Each task was committed atomically:

1. **Task 1: Prices history endpoint + watchlist repo/service (DB + tracked-set)** - `461417d` (feat)
2. **Task 2: Prices + watchlist routers and main.py registration** - `37667de` (feat)

**Plan metadata:** this commit (SUMMARY.md)

## Files Created/Modified

- `backend/app/db/watchlist_repo.py` - `list_tickers`, `add_ticker`, `remove_ticker`, `has_open_position` over `get_connection()`
- `backend/app/services/__init__.py` - `services` package barrel exporting `watchlist_service`
- `backend/app/services/watchlist_service.py` - `validate_symbol`, `list_watchlist`, `add`, `remove`
- `backend/app/api/prices.py` - `create_prices_router(cache)` factory: `GET /{ticker}/history`
- `backend/app/api/watchlist.py` - `create_watchlist_router(cache)` factory: `GET`/`POST`/`DELETE`
- `backend/app/api/__init__.py` - exports `create_prices_router`, `create_watchlist_router` alongside `health_router`
- `backend/app/main.py` - imports + registers both new routers at the documented site
- `backend/tests/api/test_watchlist.py` - repo/service unit tests (Task 1) + `TestClient` route tests (Task 2)
- `backend/tests/api/test_prices.py` - `TestClient` route tests for the history endpoint

## Decisions Made

- **Watchlist router reads the market source from `request.app.state` at request time, not from a closure.** The plan's `<action>` says to register the watchlist router "passing app.state.cache and app.state.source," but `app.state.market_source` doesn't exist until the lifespan runs — it's constructed from `db.get_tracked_tickers()`, which itself needs `db.initialize()` to have already run (APP-03's documented startup order in `app/main.py`). Router *registration* happens synchronously in `create_app()`, before the lifespan executes. `cache = PriceCache()` is created earlier (before the lifespan closure is even defined), so it can still be closed over directly — `create_prices_router(cache)` and `create_watchlist_router(cache)` both do this, matching the existing `create_stream_router(cache)` pattern. Only the market source needed the request-time indirection. This is a **Rule 3 (blocking issue)** fix: the plan's literal registration call as written would `NameError` on an undefined `source`.
- **Massive-mode unpriceable-symbol rejection is gated on `isinstance(source, SimulatorDataSource)`.** `SimulatorDataSource.add_ticker()` seeds the cache synchronously (existing behavior, unchanged), so the "give the source a brief chance" poll-and-rollback window described in the plan would never actually be exercised for the simulator — and would just add latency to the tested default path for no reason. The isinstance check keeps the poll/rollback logic real (exercised by a `FakeMarketDataSource` test) while the simulator path stays synchronous and fast.
- **Test split within `tests/api/test_watchlist.py`.** Task 1's `<files>` list names only `test_watchlist.py` for the repo/service tests; Task 2's `<files>` list names only `test_prices.py`, but its `<action>` also describes watchlist route tests (`GET`/`POST`/`DELETE`). Since the plan's top-level frontmatter `files_modified` lists both `test_prices.py` and `test_watchlist.py`, the watchlist route tests (`TestWatchlistRoutes`) were appended to the already-existing `test_watchlist.py` in Task 2, keeping prices-route tests and watchlist-route tests in their respective files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Watchlist router registration restructured to avoid a NameError on an undefined `source`**
- **Found during:** Task 2, writing the `app/main.py` router registration
- **Issue:** The plan's action text says to call `create_watchlist_router(cache, source)` at the registration site, but `source` (the market data source) is created *inside* the lifespan closure, which hasn't run yet when routers are registered in `create_app()`. Using `source` at that point would be a `NameError` — it simply doesn't exist yet.
- **Fix:** `create_watchlist_router(cache)` takes only `cache` (available at registration time, same object later exposed as `app.state.cache`). Its mutating (`POST`/`DELETE`) handlers accept a `Request` parameter and read `request.app.state.market_source` at call time — by the time any HTTP request is served, the lifespan has already completed and `market_source` is guaranteed set. `create_prices_router(cache)` is unaffected since it only ever needed `cache`.
- **Files modified:** `backend/app/api/watchlist.py`, `backend/app/main.py`
- **Verification:** `uv run --extra dev pytest tests/api/ -x -q` — 29 passed; manual `curl -XPOST localhost:8321/api/watchlist -d '{"ticker":"pypl"}'` against a live `uvicorn` process returned `{"ticker":"PYPL"}`
- **Committed in:** `37667de` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking registration-order issue). No scope creep — no threat-model or behavior changes beyond what the plan specified.

## Issues Encountered

- **Sandboxed `uv` cache directory is read-only** — `uv run` failed with "Could not acquire lock ... Read-only file system" under default sandbox restrictions on `~/.cache/uv`. Re-ran test/lint/uvicorn commands with the sandbox override for this project-local, non-destructive tooling only (same environment limitation noted in the 01-01 and 01-02 SUMMARYs, not a plan deviation).
- **Test seed-data collision** — `database.initialize()` already seeds AAPL as part of the default 10-ticker watchlist, so an initial `test_shape_without_cache_tick`/`test_shape_with_cache_tick` assertion that assumed AAPL was the *only* watchlist row failed. Fixed by asserting against the specific AAPL entry within the full 10-ticker list rather than assuming list length 1 — a test-authoring correction, not a production-code deviation.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `backend/app/services/` now exists as the business-logic layer described in `ARCHITECTURE.md`; Plan 03 (portfolio APIs) and later chat plans (05/06) can follow the same `services/*.py` + `api/*.py` router-factory pattern established here.
- `request.app.state.market_source` read-at-request-time is the pattern any future router needing the market source (not just `cache`) should follow, since the source is always lifespan-constructed.
- `watchlist_repo.has_open_position()` is exercised today only via a manually-inserted `positions` row in tests (the table is otherwise empty pre-Plan-03) — Plan 03's portfolio trade execution will be the first real writer of that table, and MKT-05's "remove keeps tracking" behavior is already correct against it.
- No blockers for downstream plans in this phase.

---
*Phase: 01-live-market-terminal*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 6 created files verified present on disk; both task commits (`461417d`, `37667de`) verified present in git log; full backend suite (123 tests) green; `ruff check app/ tests/` clean.
