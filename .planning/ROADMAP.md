# Roadmap: FinAlly — AI Trading Workstation

## Overview

FinAlly's market-data subsystem is already built and tested. This roadmap delivers the remaining
platform to a demo-ready, end-to-end trading workstation as a sequence of vertical MVP slices —
each phase lights up a complete, observable user capability rather than a horizontal technical
layer. We start by getting a live, streaming terminal in front of the user (foundation + prices),
then make it tradeable, then make performance visible, then add the AI copilot, and finally
package and harden it. Every phase ends with something the user can see and do in the browser.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Live Market Terminal** - Foundation + streaming prices + editable watchlist visible in the browser
- [ ] **Phase 2: Trading & Positions** - Buy/sell with instant fills, positions table, live header financials
- [ ] **Phase 3: Portfolio Performance & Composition** - P&L-colored heatmap and portfolio-value-over-time chart
- [ ] **Phase 4: AI Copilot Chat** - LLM chat that analyzes the portfolio and auto-executes trades & watchlist changes
- [ ] **Phase 5: Packaging & Deployment** - One-command Docker launch with persistent data and start/stop scripts
- [ ] **Phase 6: Test Hardening** - Backend, frontend, and Playwright E2E coverage of the core flows

## Phase Details

### Phase 1: Live Market Terminal

**Goal**: A user opens http://localhost:8000 and sees a live, dark trading terminal streaming the 10 seeded tickers — an editable watchlist with flashing prices, server-computed change %, populated sparklines, and a clickable main detail chart.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: DB-01, DB-02, DB-03, DB-04, APP-01, APP-02, APP-03, APP-04, MKT-01, MKT-02, MKT-03, MKT-04, MKT-05, WATCH-01, WATCH-02, WATCH-03, WATCH-04, UI-01, UI-02, UI-09, UI-10
**Success Criteria** (what must be TRUE):

  1. Opening localhost:8000 shows the dark terminal with the 10 default tickers streaming live prices that flash green (uptick) / red (downtick) and fade
  2. Each watchlist row shows a server-computed change % and a sparkline that renders already-populated (backfilled from `/api/prices/{ticker}/history`) then keeps growing from the SSE stream
  3. Clicking a ticker opens a larger detail chart that renders populated immediately then extends live
  4. The user can add a well-formed ticker (e.g. PYPL) and remove one; the change persists and streaming starts/stops accordingly (a removed ticker with an open position keeps streaming)
  5. Restarting the container preserves the watchlist (SQLite volume) and `GET /api/health` returns healthy

**Plans**: 4/6 plans executed
Plans:

- [x] 01-01-PLAN.md — Backend foundation: SQLite schema/init/seed + app/main.py wiring + health + static serving
- [x] 01-02-PLAN.md — Market-data cache extensions: session reference price, ~600pt history ring buffer, session_change_percent
- [x] 01-03-PLAN.md — Frontend scaffold + terminal shell: Next.js static export, Tailwind dark theme, live connection dot, placeholder panels
- [x] 01-04-PLAN.md — Prices & watchlist API + tracked-set (watchlist ∪ positions); router registration
- [ ] 01-05-PLAN.md — Watchlist panel UI: flashing live prices, session change %, backfilled+growing sparklines, inline add/remove
- [ ] 01-06-PLAN.md — Main detail chart UI: click-to-select, auto-select first ticker, filled-area chart backfill+live extend

**UI hint**: yes

### Phase 2: Trading & Positions

**Goal**: The user can buy and sell shares with instant market fills and watch their cash, positions table, and header portfolio value update server-side in real time.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-08, UI-03, UI-04, UI-08
**Success Criteria** (what must be TRUE):

  1. Buying via the trade bar fills instantly at the live cached price, decreases cash, and adds or updates a position (avg cost recomputed as the share-weighted average)
  2. Selling reduces the position and increases cash; selling to quantity 0 deletes the position row
  3. The positions table shows ticker, quantity, avg cost, current price, unrealized P&L and % change — all computed server-side
  4. The header shows live total portfolio value, cash balance, and a connection-status dot (green/yellow/red)
  5. An invalid trade (insufficient cash on buy, insufficient shares on sell) is rejected with an error and changes no state; money is rounded to cents

**Plans**: TBD
**UI hint**: yes

### Phase 3: Portfolio Performance & Composition

**Goal**: The user can see portfolio composition as a P&L-colored heatmap and track total portfolio value over time on a P&L chart backed by durable snapshots.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: APP-05, PORT-06, PORT-07, UI-05, UI-06
**Success Criteria** (what must be TRUE):

  1. The heatmap (treemap) renders one rectangle per open position, sized by portfolio weight and colored green (profit) / red (loss) by P&L
  2. The P&L chart plots total portfolio value over time and gains a new data point at least every 30 seconds
  3. Executing a trade immediately writes a snapshot and the new point appears on the P&L chart
  4. Reloading the page preserves the P&L history (served from `portfolio_snapshots` via `GET /api/portfolio/history`)

**Plans**: TBD
**UI hint**: yes

### Phase 4: AI Copilot Chat

**Goal**: The user can chat with the FinAlly AI copilot, which analyzes the portfolio and executes trades and watchlist changes on their behalf through natural language.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, UI-07
**Success Criteria** (what must be TRUE):

  1. Sending a chat message returns a conversational response grounded in current portfolio context plus the last 20 messages of history
  2. Asking the AI to buy or sell executes the trade through the same validated code path as manual trades, shown inline as a confirmation
  3. Asking the AI to add or remove a watchlist ticker applies the change (same validation as manual) and it appears/disappears in the watchlist
  4. The chat panel shows scrolling conversation history and a loading indicator while awaiting the response; messages and executed actions persist across reload
  5. With `LLM_MOCK=true` the chat returns deterministic responses without calling OpenRouter, and malformed model output is retried once before a graceful error

**Plans**: TBD
**UI hint**: yes

### Phase 5: Packaging & Deployment

**Goal**: A user can launch the entire application with a single script and one Docker command, with the database persisting across restarts.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):

  1. A multi-stage Dockerfile builds one image (Node builds the frontend export, Python serves it) that serves API + SSE + static UI on port 8000
  2. Running the macOS/Linux start script launches the container idempotently and the app is reachable at localhost:8000; the stop script stops it without destroying data
  3. The Windows PowerShell start/stop scripts perform the equivalent launch and stop
  4. Stopping and restarting the container preserves the database via the `/app/db` volume mount

**Plans**: TBD

### Phase 6: Test Hardening

**Goal**: The platform's core flows are protected by automated backend, frontend, and end-to-end tests that pass under the mock-LLM configuration.
**Mode:** mvp
**Depends on**: Phase 5
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):

  1. Backend pytest covers trade execution, P&L, and edge cases (oversell, insufficient cash, sell at a loss) and passes
  2. Backend pytest covers LLM structured-output parsing (including malformed responses) and the new API routes (status codes, response shapes, error handling)
  3. Frontend component tests cover rendering, price-flash animation, watchlist CRUD, and chat state
  4. Playwright E2E (with `LLM_MOCK=true`) covers fresh start, buy, sell, watchlist add/remove, chat, and SSE reconnection — and the suite runs green

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Live Market Terminal | 4/6 | In Progress|  |
| 2. Trading & Positions | 0/TBD | Not started | - |
| 3. Portfolio Performance & Composition | 0/TBD | Not started | - |
| 4. AI Copilot Chat | 0/TBD | Not started | - |
| 5. Packaging & Deployment | 0/TBD | Not started | - |
| 6. Test Hardening | 0/TBD | Not started | - |
