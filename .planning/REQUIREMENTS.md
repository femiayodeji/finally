# Requirements: FinAlly — AI Trading Workstation

**Defined:** 2026-07-14
**Core Value:** A user opens one URL and gets a live trading terminal where they can watch streaming prices, trade a simulated portfolio, and have an AI copilot execute trades and manage the watchlist — with the backend as the single authoritative source of all money math.

> Source of truth: `planning/PLAN.md` (authoritative build contract). The market-data subsystem (`backend/app/market/`) is already built and tested — see PROJECT.md *Validated* and `.planning/codebase/`. These v1 requirements cover the remaining platform to demo-ready.

## v1 Requirements

### Database

- [ ] **DB-01**: On startup (before the market-data task), the backend creates the SQLite schema (users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages) if missing
- [ ] **DB-02**: On a fresh database, the backend seeds one default user (cash `10000.0`) and the 10 default watchlist tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX)
- [ ] **DB-03**: The SQLite file persists at `db/finally.db` across restarts via the mounted volume
- [ ] **DB-04**: Every table carries a `user_id` column defaulting to `"default"` (single-user, multi-user-ready)

### App Wiring

- [ ] **APP-01**: The FastAPI app registers all routers — stream, prices, portfolio, watchlist, chat, health
- [ ] **APP-02**: The backend serves the static Next.js export for all non-`/api` routes on port 8000
- [ ] **APP-03**: The market-data background task starts at app startup, seeded from watchlist ∪ open positions
- [ ] **APP-04**: `GET /api/health` returns a healthy status for Docker/deployment checks
- [ ] **APP-05**: A background task records a `portfolio_snapshots` row every 30 seconds

### Market Data Extensions

<!-- Additive extensions to the already-built PriceCache/PriceUpdate (PLAN.md §6 note). -->

- [ ] **MKT-01**: The price cache captures a session reference (open) price per ticker on first observation after startup
- [ ] **MKT-02**: The price cache maintains a bounded rolling history ring buffer (~600 points) per ticker, in memory only
- [ ] **MKT-03**: The SSE payload and REST responses include the server-computed change % (latest vs. session reference)
- [ ] **MKT-04**: `GET /api/prices/{ticker}/history` returns recent in-memory history for chart/sparkline backfill
- [ ] **MKT-05**: The tracked set is watchlist ∪ open positions; removing a watchlist ticker keeps tracking it while a position remains open

### Portfolio

- [ ] **PORT-01**: `GET /api/portfolio` returns cash, positions, total value, and unrealized P&L — all computed server-side
- [ ] **PORT-02**: `POST /api/portfolio/trade` executes a market buy at the current cached price, rejecting insufficient cash
- [ ] **PORT-03**: `POST /api/portfolio/trade` executes a market sell, rejecting insufficient shares, and deletes the position row when quantity reaches 0
- [ ] **PORT-04**: A buy recomputes `avg_cost` as the share-weighted average; a sell leaves `avg_cost` unchanged
- [ ] **PORT-05**: Cash, price, and `avg_cost` are rounded to cents at execution
- [ ] **PORT-06**: A `portfolio_snapshots` row is written immediately after each successful trade
- [ ] **PORT-07**: `GET /api/portfolio/history` returns total-value snapshots over time for the P&L chart
- [ ] **PORT-08**: A failed trade validation returns an error and changes no state

### Watchlist

- [ ] **WATCH-01**: `GET /api/watchlist` returns the watchlist tickers with a latest-price snapshot
- [ ] **WATCH-02**: `POST /api/watchlist` adds a validated ticker (uppercased, 1–5 letters), idempotent on duplicates
- [ ] **WATCH-03**: In simulator mode any well-formed symbol is accepted with default seed/params; in Massive mode unpriceable symbols are rejected
- [ ] **WATCH-04**: `DELETE /api/watchlist/{ticker}` removes it from the watchlist; price tracking continues while a position is open

### Chat & LLM

- [ ] **CHAT-01**: `POST /api/chat` returns a structured JSON response (message + actions) via LiteLLM → OpenRouter (Cerebras)
- [ ] **CHAT-02**: LLM-issued trades auto-execute through the same validated code path as manual trades
- [ ] **CHAT-03**: LLM-issued watchlist changes (`add`/`remove`) auto-apply with the same validation as manual changes
- [ ] **CHAT-04**: The chat prompt includes current portfolio context plus the last 20 messages of history
- [ ] **CHAT-05**: The response is schema-validated before any auto-execution; malformed output is retried once, then returns a graceful error
- [ ] **CHAT-06**: With `LLM_MOCK=true`, the backend returns deterministic mock responses without calling OpenRouter
- [ ] **CHAT-07**: Chat messages and their executed actions are persisted to `chat_messages`

### Frontend UI

- [ ] **UI-01**: The watchlist grid shows ticker, live price (flashing green/red on change), server change %, and a sparkline backfilled from history then extended via SSE
- [ ] **UI-02**: Clicking a ticker shows a larger detail chart, backfilled from history then extended live
- [ ] **UI-03**: The trade bar (ticker, quantity, buy/sell) executes market orders with instant fill and no confirmation dialog
- [ ] **UI-04**: The positions table shows ticker, quantity, avg cost, current price, unrealized P&L, and % change
- [ ] **UI-05**: The portfolio heatmap (treemap) sizes each position by weight and colors it by P&L
- [ ] **UI-06**: The P&L chart plots total portfolio value over time from snapshots
- [ ] **UI-07**: The AI chat panel shows scrolling history, a loading indicator, and inline trade/watchlist confirmations
- [ ] **UI-08**: The header shows live total value, cash balance, and a connection-status indicator dot
- [ ] **UI-09**: The UI uses the dark terminal theme and specified accent colors, desktop-first and functional on tablet
- [ ] **UI-10**: After mount, prices update from the SSE stream (no REST polling for live price refreshes)

### Deployment

- [ ] **DEPLOY-01**: A multi-stage Dockerfile builds the frontend (Node) then serves the app via Python (uvicorn) on port 8000
- [ ] **DEPLOY-02**: The SQLite database persists via a volume mount to `/app/db`
- [ ] **DEPLOY-03**: Idempotent `start`/`stop` scripts exist for macOS/Linux
- [ ] **DEPLOY-04**: Idempotent `start`/`stop` scripts exist for Windows PowerShell

### Testing

- [ ] **TEST-01**: Backend pytest covers trade execution, P&L, and edge cases (oversell, insufficient cash, sell at a loss)
- [ ] **TEST-02**: Backend pytest covers LLM structured-output parsing, including malformed-response handling
- [ ] **TEST-03**: Backend pytest covers the new API routes (status codes, response shapes, error handling)
- [ ] **TEST-04**: Frontend component tests cover rendering, price-flash animation, watchlist CRUD, and chat state
- [ ] **TEST-05**: Playwright E2E (with `LLM_MOCK=true`) covers fresh start, buy, sell, watchlist add/remove, chat, and SSE reconnection

## v2 Requirements

### Cloud Deployment

- **DEPLOY-05**: Terraform configuration for AWS App Runner (or Render) in a `deploy/` directory (stretch goal)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Authentication / multi-user | Single hardcoded `user_id="default"`; schema is multi-user-ready but auth is not built (course simplification) |
| Realized P&L ledger | Only cash + `avg_cost`-based unrealized P&L; performance shown via `portfolio_snapshots` over time |
| Limit/stop orders, order book, partial fills, fees | Market orders only, instant fill — dramatically simpler portfolio math |
| WebSockets | SSE is sufficient for one-way server→client push, universal browser support |
| Postgres / external DB server | SQLite is self-contained and zero-config for single-user |
| Token-by-token LLM streaming | Cerebras inference is fast enough that a loading indicator suffices |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (populated by roadmapper) | | |

**Coverage:**
- v1 requirements: 43 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 43 ⚠️

---
*Requirements defined: 2026-07-14*
*Last updated: 2026-07-14 after initial definition*
