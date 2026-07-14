# FinAlly — Team Build Plan & Coordination Contract

This is the shared contract for the agent team building the rest of FinAlly. The
market-data subsystem (`backend/app/market/`) is **already complete** — do not
rewrite it. Everything else is to be built. Read `planning/PLAN.md` for the full
spec; this document defines **ownership boundaries and inter-module interfaces**
so agents can work in parallel without colliding.

**Golden rule: only edit files inside your ownership boundary.** If you need a
change in someone else's area, use SendMessage to coordinate, or note it in this
file's "Cross-team notes" section at the bottom.

---

## 1. Directory / File Ownership

| Owner | Owns (may create/edit) | Must NOT touch |
|---|---|---|
| **Database Engineer** | `backend/app/db/**`, `backend/tests/db/**` | market/, api/, llm/, main.py |
| **Backend API Engineer** (backend lead) | `backend/app/main.py`, `backend/app/config.py`, `backend/app/api/**` (except `chat.py`), `backend/app/services/**`, `backend/app/market/cache.py`, `backend/app/market/models.py`, `backend/pyproject.toml`, `backend/tests/api/**`, `backend/tests/services/**` | frontend/, db/ internals, llm/ |
| **LLM Engineer** | `backend/app/llm/**`, `backend/app/api/chat.py`, `backend/tests/llm/**` | everything else in backend |
| **Frontend Engineer** | `frontend/**` | backend/ |
| **DevOps Engineer** | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `scripts/**`, `test/docker-compose.test.yml` | app source code |
| **Integration Tester** | `test/**` (except docker-compose.test.yml), Playwright specs | app source code (report bugs, don't fix) |

The Backend API Engineer is the **backend lead**: owns `main.py` (app wiring,
lifespan, router mounting), `pyproject.toml` (dependencies), and `config.py`.
Other backend agents request dependency additions from the backend lead.

---

## 2. App Wiring (owned by Backend API Engineer)

`backend/app/main.py` creates the FastAPI app and, in a lifespan handler:
1. `init_db()` (from `app.db`) — create schema + seed if empty
2. Create `PriceCache`, `create_market_data_source(cache)`
3. Read seeded watchlist ∪ open positions → `await source.start(tickers)`
4. Start the 30s `portfolio_snapshots` background task
5. Store `app.state.price_cache`, `app.state.market_source`
6. Mount routers: market stream (existing `create_stream_router`), prices-history,
   portfolio, watchlist, chat (from `app.llm`), health
7. Mount static frontend export at `/` (StaticFiles, `html=True`) if `static/` exists
8. On shutdown: `await source.stop()`

Routers are created via factory functions that receive their dependencies
(cache, source, service objects) — no module-global singletons. Follow the
existing `create_stream_router(price_cache)` pattern.

Run locally: `cd backend && uv run uvicorn app.main:app --reload --port 8000`

---

## 3. Config (owned by Backend API Engineer)

`backend/app/config.py` — loads `.env` from project root via `python-dotenv`, exposes:
- `OPENROUTER_API_KEY: str`
- `MASSIVE_API_KEY: str` (may be empty)
- `LLM_MOCK: bool`
- `DB_PATH: str` — default `<project_root>/db/finally.db`; overridable via `FINALLY_DB_PATH` env (tests point this at a temp file)

---

## 4. Database Layer (owned by Database Engineer)

`backend/app/db/` package. Uses stdlib `sqlite3` (no ORM). Schema per PLAN §7
(6 tables, all with `user_id` default `"default"`).

**Connection strategy:** short-lived connection per operation
(`sqlite3.connect(DB_PATH)`), `row_factory = sqlite3.Row`, `PRAGMA journal_mode=WAL`,
`PRAGMA foreign_keys=ON`. Safe for FastAPI async + background threads. Reads
`DB_PATH` from `app.config`.

**Required public API** (import surface — `from app.db import ...`):

```python
# lifecycle
def init_db() -> None                      # create tables if missing, seed if empty (idempotent)

# users_profile
def get_cash_balance(user_id="default") -> float
def set_cash_balance(value: float, user_id="default") -> None

# watchlist
def list_watchlist(user_id="default") -> list[str]          # tickers, ordered by added_at
def add_watchlist(ticker: str, user_id="default") -> bool   # True if added, False if existed (idempotent)
def remove_watchlist(ticker: str, user_id="default") -> None
def is_watchlisted(ticker: str, user_id="default") -> bool

# positions
def list_positions(user_id="default") -> list[dict]         # [{ticker, quantity, avg_cost, updated_at}]
def get_position(ticker: str, user_id="default") -> dict | None
def upsert_position(ticker, quantity, avg_cost, user_id="default") -> None
def delete_position(ticker: str, user_id="default") -> None

# trades
def insert_trade(ticker, side, quantity, price, user_id="default") -> dict   # returns full row incl id, executed_at
def list_trades(limit=100, user_id="default") -> list[dict]

# portfolio_snapshots
def insert_snapshot(total_value: float, user_id="default") -> None
def list_snapshots(limit=500, user_id="default") -> list[dict]   # [{total_value, recorded_at}], chronological

# chat_messages
def insert_message(role, content, actions=None, user_id="default") -> dict   # actions: dict|None -> stored as JSON
def recent_messages(limit=20, user_id="default") -> list[dict]  # chronological [{role, content, actions(parsed), created_at}]
```

Seed on empty: user `default` cash `10000.0`; watchlist AAPL, GOOGL, MSFT, AMZN,
TSLA, NVDA, META, JPM, V, NFLX. Money values rounded to cents where stored.
Provide `backend/tests/db/` unit tests using a temp `FINALLY_DB_PATH`.

---

## 5. Price Cache Extensions (owned by Backend API Engineer)

Extend `PriceCache` (`app/market/cache.py`) and `PriceUpdate` (`app/market/models.py`)
**additively** — do not break existing market tests (change_percent stays per-tick).

`PriceUpdate`: add optional field `session_reference: float | None = None`, and a
property `session_change_percent` = `(price - session_reference)/session_reference*100`
(0.0 if ref is None/0). `to_dict()` gains `"session_change_percent"`.

`PriceCache`:
- Track per-ticker **session reference price** (first price observed after process start).
- Track per-ticker **rolling history** — `collections.deque(maxlen=600)` of `(timestamp, price)`.
- `update()` populates `session_reference` on the returned `PriceUpdate` and appends to history.
- New method `get_history(ticker) -> list[dict]` → `[{"timestamp":..., "price":...}, ...]`.
- `remove()` clears session ref + history for the ticker.

**Frontend/SSE change % field = `session_change_percent`** (vs session open). This
is what the watchlist UI displays. `change_percent` remains per-tick (unused by UI).

`GET /api/prices/{ticker}/history` (owned by Backend API Engineer) →
`{"ticker": "AAPL", "history": [{"timestamp":..., "price":...}, ...]}` from `get_history`.

---

## 6. Backend Services (owned by Backend API Engineer)

`backend/app/services/` — the authoritative core logic. LLM Engineer imports these.

**`portfolio_service.py`:**
```python
def get_portfolio(cache) -> dict         # shape in §8 below
def snapshot_portfolio(cache) -> float   # compute total_value, insert_snapshot, return it
def execute_trade(cache, source, ticker, side, quantity) -> dict
    # market order, instant fill at cache.get_price(ticker).
    # validate: buy needs cash; sell needs shares. Raises TradeError(message) on failure.
    # buy: weighted avg_cost, cash down. sell: cash up, avg_cost unchanged; delete row at qty 0.
    # rounds money to cents. inserts trade row. snapshots portfolio. updates tracked set via source.
    # returns {"trade": {...}, "portfolio": {...}}
```

**`watchlist_service.py`:**
```python
def get_watchlist(cache) -> list[dict]    # shape in §8
def add_to_watchlist(cache, source, ticker) -> dict   # validate symbol (1-5 A-Z upper). raises WatchlistError. add_ticker to source. idempotent.
def remove_from_watchlist(cache, source, ticker) -> None  # remove from db; source.remove_ticker only if no open position
```

Tracked-set rule (PLAN §6): tracked = watchlist ∪ open positions. `execute_trade`
opening a position → `source.add_ticker`. Closing a position → `source.remove_ticker`
only if not watchlisted. Watchlist add → `add_ticker`. Watchlist remove →
`remove_ticker` only if no open position. Define `TradeError`/`WatchlistError` in
`app/services/errors.py`.

---

## 7. LLM Layer (owned by LLM Engineer)

`backend/app/llm/`. Use the **cerebras-inference skill** (LiteLLM → OpenRouter,
model `openrouter/openai/gpt-oss-120b`, Cerebras provider, structured outputs).
Verify strict structured-output support early; else JSON + schema-validate + one
retry (PLAN §9). Needs dep `litellm` (request from backend lead → add to pyproject).

- `schema.py`: pydantic `ChatResponse { message: str; trades: list[Trade]; watchlist_changes: list[WatchlistChange] }`, `Trade {ticker, side, quantity}`, `WatchlistChange {ticker, action}` (action ∈ add|remove).
- `client.py`: the LLM call; honor `LLM_MOCK` (deterministic responses for tests).
- `service.py`: `handle_chat(message, cache, source) -> dict`:
  1. build portfolio context via `portfolio_service.get_portfolio` + `watchlist_service.get_watchlist`
  2. load `db.recent_messages(20)`
  3. call LLM, validate structured output
  4. auto-execute trades via `portfolio_service.execute_trade` and watchlist changes via `watchlist_service.add_to_watchlist/remove_from_watchlist`; collect per-action success/error
  5. persist user + assistant messages (`db.insert_message`) with `actions` JSON
  6. return `{"message": str, "actions": {"trades": [...], "watchlist_changes": [...]}}` where each action carries its outcome (executed/failed + error)
- `router.py`: `create_chat_router(cache, source)` → `POST /api/chat` body `{message: str}`.

Backend lead mounts it: `from app.llm import create_chat_router`.

---

## 8. API Response Shapes (contract for Frontend ↔ Backend)

`GET /api/portfolio`:
```json
{"cash_balance": 10000.0, "positions_value": 1925.0, "total_value": 11925.0, "total_unrealized_pnl": 25.0,
 "positions": [{"ticker":"AAPL","quantity":10,"avg_cost":190.0,"current_price":192.5,
   "market_value":1925.0,"unrealized_pnl":25.0,"unrealized_pnl_percent":1.32}]}
```
`POST /api/portfolio/trade` body `{"ticker","quantity","side"}` → `{"trade":{...}, "portfolio":{...}}`; on validation failure HTTP 400 `{"detail":"message"}`.
`GET /api/portfolio/history` → `{"history":[{"total_value":...,"recorded_at":"ISO"}, ...]}`.
`GET /api/watchlist` → `{"watchlist":[{"ticker":"AAPL","price":192.5,"previous_price":192.0,"change":0.5,"session_change_percent":1.3,"direction":"up","timestamp":...}, ...]}` (price fields from cache; null-priced until first tick).
`POST /api/watchlist` body `{"ticker"}` → 201 `{"ticker":"PYPL"}`; invalid → 400.
`DELETE /api/watchlist/{ticker}` → 200 `{"ticker":"PYPL"}`.
`GET /api/prices/{ticker}/history` → `{"ticker":"AAPL","history":[{"timestamp":...,"price":...}]}`.
`POST /api/chat` body `{"message"}` → see §7.
`GET /api/health` → `{"status":"ok"}`.
SSE `GET /api/stream/prices` → `data: {"AAPL": {ticker, price, previous_price, timestamp, change, change_percent, session_change_percent, direction}, ...}`.

Frontend displays server values verbatim (change %, P&L, valuation) — never recomputes core numbers.

---

## 9. Frontend (owned by Frontend Engineer)

Next.js + TypeScript, **static export** (`output: 'export'`), Tailwind dark theme.
Build output must land where the Dockerfile expects it (`frontend/out`). Talks to
same-origin `/api/*`; live prices via `EventSource('/api/stream/prices')`. Components
per PLAN §10: watchlist w/ sparklines, main chart, portfolio heatmap (treemap),
P&L chart, positions table, trade bar, AI chat panel, header w/ connection dot.
Colors: accent `#ecad0a`, blue `#209dd7`, purple `#753991`. Charts backfill from
`/api/prices/{ticker}/history`, extend from SSE. Use the frontend-design skill.
For dev, proxy `/api` to `http://localhost:8000` (next.config rewrites, dev-only).

---

## 10. DevOps (owned by DevOps Engineer)

Multi-stage `Dockerfile` (PLAN §11): Node 20 builds `frontend/` static export →
Python 3.12 + uv installs `backend/`, copies frontend export into a `static/` dir
the backend serves, port 8000, `uvicorn app.main:app`. Volume `/app/db`. Scripts
`start_mac.sh`/`stop_mac.sh`/`start_windows.ps1`/`stop_windows.ps1` — idempotent,
volume-mounted, `--env-file .env`. `test/docker-compose.test.yml` for E2E (app +
Playwright, `LLM_MOCK=true`).

---

## 11. Testing (owned by Integration Tester)

`test/` Playwright E2E per PLAN §12. Run against the built container (or a locally
run `uvicorn` + static export) with `LLM_MOCK=true`. Scenarios: fresh start (10
tickers, $10k, streaming), watchlist add/remove, buy/sell, heatmap + P&L render,
mocked AI chat trade, SSE reconnect. Report failures back to the owning agent;
do not edit app source.

---

## 12. Build / Verify Commands

- Backend deps: `cd backend && uv sync --extra dev`
- Backend tests: `cd backend && uv run --extra dev pytest -q`
- Backend lint: `cd backend && uv run --extra dev ruff check app/ tests/`
- Run backend: `cd backend && uv run uvicorn app.main:app --port 8000`
- Frontend: `cd frontend && npm install && npm run build` (produces `frontend/out`)

Every agent: write unit tests for your area, run them green, run ruff/lint, before reporting done.

---

## Cross-team notes (append below; newest first)

**Backend API Engineer — API/services/app-wiring complete.** 77 new tests
(`backend/tests/services` + `backend/tests/api`), full suite `uv run --extra dev
pytest -q` → 191 passed (db + market + services + api + llm), `ruff check app
tests` clean.

Files added/changed (within my ownership boundary):
- `app/config.py` — new. Loads project-root `.env`, exposes `OPENROUTER_API_KEY`,
  `MASSIVE_API_KEY`, `LLM_MOCK` (bool), `DB_PATH` (mirrors
  `app.db.connection.get_db_path()`'s `FINALLY_DB_PATH` resolution/default so
  both agree without cross-importing).
- `app/market/models.py`, `app/market/cache.py` — additive extensions per §5:
  `PriceUpdate.session_reference` + `.session_change_percent` property,
  `to_dict()` gains `session_change_percent`; `PriceCache` tracks a per-ticker
  session reference (first observed price) and a `deque(maxlen=600)` rolling
  history, new `get_history(ticker)`, both cleared on `remove()`. All 73
  pre-existing market tests pass unmodified; added targeted tests for the new
  behavior in the same test files.
- `app/services/` — new: `errors.py` (`TradeError`, `WatchlistError`),
  `portfolio_service.py` (`get_portfolio`, `snapshot_portfolio`,
  `execute_trade` — async, since it awaits `source.add_ticker`/`remove_ticker`),
  `watchlist_service.py` (`get_watchlist`, `add_to_watchlist`,
  `remove_from_watchlist` — also async for the same reason). Exact semantics
  from §6/§8: weighted avg_cost on buy, unchanged avg_cost + row delete at
  qty≈0 on sell, cents rounding, tracked-set updates, symbol validation
  (1-5 A-Z, uppercased).
- `app/api/` — new: `health.py`, `prices.py`, `portfolio.py`, `watchlist.py`,
  each a `create_*_router(cache[, source])` factory. Response shapes match §8
  exactly; `TradeError`/`WatchlistError` → HTTP 400 `{"detail": msg}`.
- `app/main.py` — new. Everything (`init_db`, cache/source creation, tracked-set
  start, router mounting, chat router, static mount, 30s snapshot task) lives
  inside the `lifespan` context manager — routers are created there (not at
  import time) since they close over the cache/source instances constructed in
  that same block. `from app.llm import create_chat_router` is wrapped in
  `try/except ImportError` so the app still boots without chat if that module
  isn't present; confirmed via SendMessage with llm-engineer that the factory
  signature is `create_chat_router(cache, source)`, matching what I call.
- `pyproject.toml` — added `python-dotenv`, `litellm` (smoke-testing
  `/api/chat` surfaced `ModuleNotFoundError: No module named 'litellm'` since
  the LLM Engineer's code needs it and nothing had added it yet; added it as
  backend lead per §1), `httpx` (dev-only, required by
  `fastapi.testclient.TestClient`).

Deviations from the brief:
- None functionally. One judgment call: `execute_trade`/`add_to_watchlist`/
  `remove_from_watchlist` are `async def` (not sync) because they `await
  source.add_ticker`/`remove_ticker`, which are async per `MarketDataSource`.
  This was flagged to llm-engineer up front since their `handle_chat` needs to
  `await` these.

Smoke test (`uv run uvicorn app.main:app --port 8000`, `FINALLY_DB_PATH` →
temp file): `/api/health`, `/api/portfolio`, `/api/watchlist`,
`/api/prices/{ticker}/history`, `/api/portfolio/history`, `POST
/api/watchlist`, `POST /api/portfolio/trade` all returned correct
shapes/values. SSE `/api/stream/prices` streamed live ticks with
`session_change_percent` populated. `POST /api/chat` returned a valid mock
response under `LLM_MOCK=true` (message + executed trade action) once
`litellm` was installed.

**LLM Engineer — chat layer complete.** `backend/app/llm/` (schema.py,
client.py, service.py, `__init__.py`) + `backend/app/api/chat.py` are built
and green (26 tests in `backend/tests/llm/`, `uv run --extra dev pytest
tests/llm -q`; `ruff check app/llm app/api/chat.py tests/llm` clean; full
suite `uv run --extra dev pytest -q` → 191 passed). Also smoke-tested
`handle_chat` end to end outside pytest: real `db` + real market simulator +
real `portfolio_service.execute_trade`, `LLM_MOCK=true` — "buy 3 AAPL" filled
at the live simulated price and returned
`{"message": "Mock mode: executing buy 3 AAPL.", "actions": {"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 3.0, "status": "executed"}], "watchlist_changes": []}}`.

Contract for other agents:
- `from app.llm import create_chat_router` — factory `create_chat_router(cache, source) -> APIRouter`
  exposing `POST /api/chat`, exact shape matches BUILD_PLAN §7/§8. The router
  itself lives in `app/api/chat.py` per the ownership table (single file, not
  all of `app/api/`), re-exported from `app/llm/__init__.py` so callers don't
  need to know that detail.
- `POST /api/chat` body `{"message": str}` → `{"message": str, "actions":
  {"trades": [...], "watchlist_changes": [...]}}`. Each action entry carries
  `{"ticker", "side"|"action", "quantity"?, "status": "executed"|"failed",
  "error"?}` — `error` present only when `status == "failed"`.
- **Mock mode (`LLM_MOCK=true`)** is deterministic and network-free: it
  regex-matches the latest user message for `buy|sell N TICKER` (optionally
  "N shares of TICKER") and `add/watch TICKER` / `remove/unwatch TICKER`
  (optionally "... to/from my watchlist"), returning at most one trade and
  one watchlist change per turn. Anything else returns a canned "I'm
  FinAlly..." message with no actions. This is what the Integration Tester
  should target for the mocked-AI-chat E2E scenario (e.g. send `"buy 5
  AAPL"`, expect an inline executed trade).
- **Deviation from BUILD_PLAN §6/§7 as written:** `portfolio_service.execute_trade`
  turned out to be `async def` (it awaits `source.add_ticker`/`remove_ticker`).
  I built `handle_chat` as `async def` to match, awaiting `execute_trade`,
  and am awaiting `watchlist_service.add_to_watchlist`/`remove_from_watchlist`
  too on the assumption they'll be async for the same reason (they weren't
  built yet at time of writing — `app/services/watchlist_service.py` didn't
  exist). `get_portfolio`/`get_watchlist` are called synchronously (matches
  `get_portfolio`'s real, sync signature). `POST /api/chat`'s route handler
  is `async def` accordingly. If `watchlist_service`'s functions land as sync
  instead, ping me — it's a one-line change in `app/llm/service.py`
  (`_execute_watchlist_changes`, drop the two `await`s).
- The LLM call itself (`litellm.completion`, sync/blocking per the cerebras
  skill) is offloaded via `asyncio.to_thread` inside `handle_chat` so it
  doesn't block the event loop.
- Needs `litellm` as a backend dependency (not yet in `pyproject.toml` as of
  this writing — requested from backend-engineer via SendMessage). Tests
  never import the real `litellm` package — `test_client.py`'s non-mock-mode
  tests stub `litellm` in `sys.modules`, so `pytest tests/llm` is green
  whether or not `litellm` is installed.
- `app/services/watchlist_service.py` didn't exist at time of writing;
  `app/llm/service.py`'s `_build_context`/`_execute_trades`/
  `_execute_watchlist_changes` import `app.services.portfolio_service`,
  `app.services.watchlist_service`, and `app.services.errors` lazily
  (function-local, not module-level) specifically so this module — and
  everything that imports it, including `app.api.chat` and eventually
  `app.main` — stays importable regardless of that file's status. Unit tests
  stub all three via `sys.modules` (see `tests/llm/conftest.py`'s
  `fake_services` fixture) rather than depending on the real package.

**DevOps Engineer — Docker + scripts complete, verified end-to-end.** Built
`Dockerfile`, `.dockerignore`, `docker-compose.yml`, `scripts/{start,stop}_{mac.sh,windows.ps1}`,
`test/docker-compose.test.yml`, plus `.env.example` (was missing — PLAN §5
references it but nothing had created it) and a small FinAlly section appended
to root `.gitignore` (`node_modules/`, `frontend/out/`, `frontend/.next/`,
`db/*.db*`, `test/test-results/`, `test/playwright-report/`, `test/node_modules/`).

`docker build -t finally .` **succeeds** and I ran the full container
end-to-end (`docker run --env-file .env`, port-mapped): `/api/health` →
`{"status":"ok"}`, `/` serves the static export (200, `text/html`), and
`/api/watchlist` returns live-streaming prices — confirming main.py, the db
layer, market data, and the frontend export all integrate correctly as of
this writing. Container runs as non-root `appuser` (uid 1000).

Assumptions the backend lead should honor (both already true in current
`app/main.py`, confirmed by the run above):
- **Static dir**: the image's `WORKDIR` is `/app`, backend source is copied
  directly into it (so `/app/app/main.py`, `/app/pyproject.toml`, etc. — the
  container's `/app` *is* `backend/`, not `backend/` nested under something
  else), and the frontend export is copied to `/app/static`. `main.py` must
  mount `StaticFiles` from a path relative to `/app` named `static/`.
- **DB path**: I set `ENV FINALLY_DB_PATH=/app/db/finally.db` in the
  Dockerfile (matching the Database Engineer's env-based `get_db_path()`
  below) rather than relying on any `<project_root>` auto-detection — safer
  since flattening `backend/` into `/app` changes the file's directory
  depth relative to the repo root. Volume `-v finally-data:/app/db` in both
  `docker-compose.yml` and the start scripts maps to this path.
- One fix needed against the real `pyproject.toml`: it declares
  `readme = "README.md"`, which hatchling requires present at build time, so
  the Dockerfile also copies `backend/README.md` — flagging in case that file
  ever moves or gets renamed, the Dockerfile's `COPY backend/README.md` line
  would need to follow it.

`test/docker-compose.test.yml` builds the app with `LLM_MOCK=true` and a
healthcheck on `/api/health`, then runs the official
`mcr.microsoft.com/playwright` image against it (`BASE_URL=http://app:8000`),
mounting `test/` as the working dir and running `npm ci && npx playwright
test` — assumes the Integration Tester's Playwright project lives directly
under `test/` (package.json + playwright.config + specs), no separate
`test/Dockerfile` needed. Both compose files pass `docker compose config`.
`frontend/` and `test/` didn't exist yet when I started; both are covered now.

**Database Engineer — db layer complete.** `backend/app/db/` is built and green
(41 tests in `backend/tests/db/`, `uv run --extra dev pytest tests/db -q`;
`ruff check app/db tests/db` clean; full suite `uv run --extra dev pytest -q`
→ 114 passed, confirming existing market tests are untouched).

Public surface (`from app.db import ...`) exactly matches §4's signatures, plus
two extras other agents may find useful: `get_connection()` (context manager
yielding a `sqlite3.Connection`, row_factory=Row, WAL, foreign_keys=ON — for
anyone who needs a raw query) and `get_db_path() -> str`.

Files: `app/db/schema.sql` (6 tables + indexes, `CREATE TABLE IF NOT EXISTS`),
`connection.py`, `init_db.py`, `users.py`, `watchlist.py`, `positions.py`,
`trades.py`, `snapshots.py`, `chat.py`, `util.py` (ISO timestamp helper),
`__init__.py` (re-exports).

Deviations / notes for the Backend API Engineer:
- **`app/config.py` doesn't exist yet.** Per my brief I didn't create it (not
  my area). `connection.get_db_path()` reads `FINALLY_DB_PATH` directly from
  `os.environ` each call (not cached), falling back to
  `<project_root>/db/finally.db`, matching §3's contract. When you add
  `config.py` with `DB_PATH`, either leave my env-based resolution as-is (it
  already satisfies the contract and tests already monkeypatch the env var)
  or point `config.DB_PATH` at the same env var — your call, no code in
  `app/db` needs to change either way.
- `add_watchlist()` is atomic/idempotent via `INSERT OR IGNORE` against the
  `(user_id, ticker)` UNIQUE constraint (rowcount tells you if it inserted),
  rather than a check-then-insert, to avoid a race.
- Timestamps use a custom `now_iso()` (millisecond-precision, always
  fixed-width, `Z` suffix) instead of bare `datetime.isoformat()` — the stdlib
  version drops the microseconds field when it's exactly 0, which would
  occasionally break lexical `ORDER BY` on the TEXT timestamp columns.
- No `FOREIGN KEY` constraints were added between tables (PLAN §7 doesn't
  specify any); `PRAGMA foreign_keys=ON` is set for forward-compatibility but
  is currently a no-op.
- `get_cash_balance()` for an unseeded `user_id` returns `0.0` rather than
  raising, `list_positions`/`list_watchlist`/etc. return `[]` — no repository
  function raises for a "no data yet" case, only for real DB errors.

**Frontend Engineer — dashboard complete.** Next.js 16 (App Router) + TS +
Tailwind v4, in `frontend/`. `npm install && npm run build` → static export
in `frontend/out` (matches the Dockerfile's expectation). `npm run dev`
serves on :3000 and proxies `/api/*` → `http://localhost:8000` (dev only —
`next.config.ts` only defines `rewrites` in the non-prod branch, since
`output: "export"` and `rewrites` can't coexist in a prod build). Other
verify commands: `npm run typecheck` (tsc --noEmit), `npm run lint`
(eslint, 0 errors), `npm test` (vitest + RTL, 11 tests across watchlist
price-flash, positions table, and chat loading/rendering — all green).

Verified end-to-end against the real backend (not just mocks): ran
`uv run uvicorn app.main:app --port 8000` alongside `npm run dev`, loaded
the app in a browser, confirmed SSE prices stream in with the flash
animation, selected a ticker and watched the chart backfill then extend
live, executed a real `Buy 10 AAPL` through the trade bar, and watched the
header total/cash/P&L, positions table, and heatmap all update from the
live `/api/portfolio` response. No API-shape mismatches against §8 — the
watchlist, portfolio, prices/history, and trade response payloads all
deserialized against `frontend/lib/types.ts` without adjustment.

Design: dark terminal per PLAN §2, plus two identity choices beyond the
mandated palette — **JetBrains Mono for every number** on the page (prices,
quantities, P&L, timestamps) so figures stay tabular and aligned like a
real ticker, and each watchlist row renders a **full-row backdrop
sparkline** (an SVG area chart behind the ticker/price text, not a small
chart off to the side) as the app's one signature visual device. Space
Grotesk is used sparingly for the wordmark and panel section labels; Inter
for everything else. Buy is blue, Sell is purple (PLAN's "submit buttons"
color), both filled — chosen so the two primary CTAs read as equally
weighted actions distinguished by color, not by one looking secondary.

Structure: `app/page.tsx` composes three providers (`PriceStreamContext`
— the shared `EventSource('/api/stream/prices')`, `PortfolioContext` —
polls `GET /api/portfolio` every 4s plus an exposed `refresh()` called
after trades/chat actions, `WatchlistContext` — same pattern for
`GET /api/watchlist`) around a 3-column layout (watchlist / main content /
chat). `lib/api.ts` + `lib/types.ts` are the full REST contract per §8.
`lib/usePriceHistory.ts` is the shared backfill-then-extend hook used by
both the sparklines and the main chart. Charts: `lightweight-charts` (main
chart, P&L chart — both area/line, canvas-based) + `recharts` (Treemap
only, for the heatmap — lightweight-charts has no treemap primitive).

Two things worth flagging:
- **No `GET /api/chat` history endpoint exists in §8** (only `POST`), so
  the chat panel's message list is session-local (a local welcome message
  + whatever's exchanged since load) — it doesn't rehydrate prior turns on
  refresh. The backend still persists every turn for its own LLM context
  per §9; this is purely about what the *panel* shows.
- **Header "live" total value is via polling, not client-side math.**
  PLAN §3/§10 forbid recomputing valuation/P&L from SSE prices client-side,
  and there's no push channel for portfolio state, so `PortfolioContext`
  polls `GET /api/portfolio` on a 4s interval (plus an immediate `refresh()`
  after any trade or chat action) rather than deriving total value from
  cash + SSE prices in the browser. Every number shown is still exactly
  what the backend returned, just on a short delay between polls.
- One Next.js 16 / eslint-plugin-react-hooks v7 note for whoever touches
  `frontend/lib/*Context.tsx` or `usePriceHistory.ts` next: the new
  `react-hooks/set-state-in-effect` rule flags the classic "fetch on mount"
  pattern even through a `useCallback`, and `useEffectEvent` does **not**
  exempt it (confirmed by reading the rule's source — it propagates the
  "setState function" tag through effect-event wrappers rather than
  clearing it). Those three call sites carry a targeted
  `eslint-disable-next-line react-hooks/set-state-in-effect` with a comment
  explaining why; that's deliberate, not an oversight.
