# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, backfilled from the backend's recent price history on load and extended live from the SSE stream (sparklines render populated, then keep growing)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Core Principle: the Backend Owns the Core

The backend is the single source of truth for all core state and computation. Portfolio valuation, P&L, price change %, and short-term price history are computed and held **server-side**; the frontend is a thin rendering layer that displays backend-computed values and never derives core numbers itself. Even where computing on the client would be marginally faster, the core stays on the server. This buys:

- **Scalability** — the in-memory price cache/history layer is the one seam that becomes a shared store (e.g., Redis) for horizontal, multi-user scaling later, with no change to the frontend or the computation logic
- **Security** — all validation (trades, watchlist, LLM-issued actions) and money math happen server-side; the client is never trusted to compute or enforce anything
- **Reliability & consistency** — every client sees the same authoritative numbers, independent of any single browser session; charts and change % survive reloads because their reference data lives on the server

Speed is still a priority — it is achieved with fast inference (Cerebras), in-memory caches, and SSE push, **not** by offloading core logic to the client.

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Static Next.js export | Single origin, no CORS issues, one port, one container, simple deployment |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── db/                   # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Optional convenience wrapper
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/db/`** contains schema SQL definitions and seed logic. The backend lazily initializes the database on first request — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts via Docker volume.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies
- **New tickers get default parameters** — a ticker added without a curated seed entry is assigned a deterministic default seed price derived from its symbol (stable across restarts) plus default drift/volatility and no correlation group. Any well-formed symbol therefore "just works" without a hand-authored entry.

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for the union of all watched tickers on a configurable interval
- Free tier (5 calls/min): poll every 15 seconds
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator

### Tracked Ticker Set

The set of tickers the price source tracks — and therefore streams over SSE — is the **union of the watchlist and every ticker with an open position**, not the watchlist alone. A user can sell part of a holding, remove that ticker from the watchlist, and still own shares; portfolio valuation (§8) needs a live price for every held ticker.

- Adding a watchlist ticker, or opening a new position, adds the ticker to the tracked set
- Removing a watchlist ticker stops tracking it **only if no open position remains** for that ticker
- A ticker with neither a watchlist entry nor an open position is dropped from tracking

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds, per ticker: the latest price, previous price, timestamp, a **session reference (open) price** captured on first observation after process start, and a **bounded rolling price history** (ring buffer, ~600 points ≈ the last few minutes at 500ms)
- The cache computes **change %** server-side (latest vs. session reference) so every client sees the same value — the frontend never computes it
- SSE streams and REST endpoints both read from this cache; it is the single source of truth for prices, history, and change %
- **History is in-memory only** — not persisted to SQLite (per-tick DB writes would be wasteful and hurt latency). Durable time-series persistence is reserved for `portfolio_snapshots` (§7). The rolling buffer resets on restart; charts backfill from it on connect and extend live via SSE
- This layer is the seam for future multi-user scaling: it moves to a shared store (e.g., Redis) without touching downstream code

> **Note:** the market-data subsystem (`MARKET_DATA_SUMMARY.md`) is already built with latest/previous/timestamp. The session reference price, rolling history buffer, and server-side change % are **additive extensions** to `PriceCache`/`PriceUpdate` to satisfy the backend-owns-the-core principle (§3).

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- Server pushes price updates for all tracked tickers (watchlist ∪ open positions, see above) at a regular cadence (~500ms)
- Each SSE event contains ticker, price, previous price, timestamp, change direction, and the backend-computed **change %** (vs. session reference)
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Initialization on Startup

The backend initializes the SQLite database **on startup, before the market-data background task starts**. If the file doesn't exist or tables are missing, it creates the schema and seeds default data; the market-data task then reads the seeded watchlist to know what to track. This means:

- No separate migration step
- No manual database setup
- Fresh Docker volumes start with a clean, seeded database automatically
- The price task always has a populated watchlist to seed tracking at boot (no lazy first-request gap)

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users_profile** — User state (cash balance)
- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, and immediately after each trade execution.
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Realized P&L — Out of Scope

The platform tracks only **cash** and `avg_cost`-based **unrealized** P&L. Realized gains/losses from sells are intentionally not stored; account performance is represented by total portfolio value over time (`portfolio_snapshots`). If the chat assistant is asked "how much have I made?", it reasons from unrealized P&L plus cash, not a realized-gains ledger.

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates (incl. server-computed change %) |
| GET | `/api/prices/{ticker}/history` | Recent in-memory price history for a ticker (backfills charts/sparklines on load) |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` (validated — see below) |
| DELETE | `/api/watchlist/{ticker}` | Remove from watchlist; price tracking continues while a position is still open |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

### Trade Execution Semantics

`POST /api/portfolio/trade` and LLM-issued trades share one code path:

- **Market order, instant fill** at the current cached price for the ticker
- **Validation**: buys require sufficient cash; sells require sufficient shares held. Failed validation returns an error (surfaced to the user, or to the LLM for chat-issued trades) and changes nothing
- **Buy**: `avg_cost` is recomputed as the share-weighted average of the existing lot and the new fill; cash decreases by `quantity × price`
- **Sell**: `avg_cost` is unchanged; cash increases by `quantity × price`. When the resulting quantity reaches 0, the position **row is deleted** (positions has UNIQUE `(user_id, ticker)`; the heatmap and positions table iterate live rows)
- **Money precision**: cash, price, and `avg_cost` are rounded to cents (2 dp) at execution to keep the ledger clean
- **Snapshot**: a `portfolio_snapshots` row is written immediately after a successful trade (in addition to the 30s cadence)
- Opening a position adds its ticker to the tracked set (§6); a fully-closed position drops out of tracking unless it is still on the watchlist

### Watchlist Validation

`POST /api/watchlist` validates the ticker before adding:

- Normalized to uppercase; must match a simple symbol format (1–5 letters)
- **Simulator mode**: any well-formed symbol is accepted — unknown tickers get a deterministic default seed price and default GBM parameters (§6)
- **Massive mode**: the symbol must resolve to real data; symbols Massive can't price are rejected as invalid
- Duplicate adds are idempotent (UNIQUE `(user_id, ticker)`)

---

## 9. LLM Integration

When writing code to make calls to LLMs, use cerebras-inference skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads recent conversation history from the `chat_messages` table, capped at the **last 20 messages** (~10 exchanges) so the prompt stays bounded as history grows
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells)
- `watchlist_changes` (optional): Array of watchlist modifications. Each entry's `action` is `"add"` or `"remove"` (mirroring `POST`/`DELETE /api/watchlist`); adds go through the same validation as manual adds (§8)

### Structured Output Reliability

Strict structured-output (JSON-schema) support on `openrouter/openai/gpt-oss-120b` via Cerebras must be verified early against the provider (per the cerebras skill). If the provider does not strictly enforce the schema, the backend falls back to: request JSON, parse and validate against the schema, and retry once on malformed output before returning a graceful error. Either way the backend **validates the response before auto-executing any trade** — it never acts on an unvalidated payload.

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (e.g., insufficient cash), the error is included in the chat response so the LLM can inform the user.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), change % (server-computed, from the SSE payload — the frontend just displays it), and a sparkline mini-chart backfilled from `/api/prices/{ticker}/history` on load and extended live from SSE
- **Main chart area** — larger chart for the currently selected ticker, price over time. Clicking a ticker in the watchlist selects it here. On selection the series is fetched from `/api/prices/{ticker}/history` so it renders populated immediately, then extended live from the SSE stream.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Canvas-based charting library preferred (Lightweight Charts or Recharts) for performance
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme
- **Backend owns the numbers (§3).** Change %, P&L, valuation, and price history all come from the server ready-to-render; the frontend does not compute them. Charts backfill from `/api/prices/{ticker}/history`, then extend from SSE
- **SSE is the source of truth for live prices.** REST responses (`/api/watchlist`, `/api/portfolio`) carry a price snapshot for initial paint only; after mount the frontend updates prices from the SSE stream and does not poll REST endpoints for price refreshes
- **Change % is stable across reloads** because its reference (session open) lives in the server-side cache and is delivered in the SSE payload — every client and every tab agrees

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Docker Volume

The SQLite database persists via a named Docker volume:

```bash
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

The `db/` directory in the project root maps to `/app/db` in the container. The backend writes `finally.db` to this path.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):
- Stops and removes the running container
- Does NOT remove the volume (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows.

All scripts should be idempotent — safe to run multiple times.

### Optional Cloud Deployment

The container is designed to deploy to AWS App Runner, Render, or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up the app container plus a Playwright container. This keeps browser dependencies out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection

---

## 13. Resolved Design Decisions

_Outcomes of the documentation review. Each decision has been folded into the sections above; this log records what was decided and why. The market-data subsystem (§6) was already complete per `MARKET_DATA_SUMMARY.md`, so several of these were informed by what that implementation actually does._

1. **Tracked ticker set = watchlist ∪ open positions** (§6 *Tracked Ticker Set*, §8). Price tracking and the SSE stream cover every held ticker, not just the watchlist. `DELETE /api/watchlist/{ticker}` stops tracking only when no open position remains — otherwise portfolio valuation would lose the price it needs.

2. **Unknown tickers** (§6, §8 *Watchlist Validation*). Simulator mode accepts any well-formed symbol, assigning a deterministic default seed price (stable across restarts) + default GBM params so new tickers "just work" for the demo. Massive mode rejects symbols it can't price. Both paths validate symbol format (1–5 letters, uppercased) first.

3. **DB initialized on startup** (§7). Schema creation + seeding happen at startup, before the market-data task reads the watchlist. The ambiguous "or first request" wording is gone.

4. **Backend-owned price history & change %** (§3, §6, §8, §10). Per the *backend owns the core* principle, the server maintains a bounded in-memory rolling price history (ring buffer) and a session reference price per ticker, computes **change %** server-side, and exposes history via `GET /api/prices/{ticker}/history`. Charts and sparklines backfill from that endpoint on load and extend live via SSE; change % is delivered in the SSE payload. History is **in-memory only** (not persisted to SQLite — per-tick writes would hurt latency); the durable time series remains `portfolio_snapshots`. _(This supersedes the review's earlier client-side "session change %" simplification, which was reversed at the user's direction to keep core logic on the backend.)_

5. **`watchlist_changes.action`** (§9) — allowed values are `"add"` and `"remove"`, mirroring the watchlist endpoints.

6. **Position closed at qty 0** (§8 *Trade Execution Semantics*) — the position row is deleted when quantity reaches 0.

7. **Realized P&L out of scope** (§7) — only cash and unrealized (`avg_cost`-based) P&L are tracked; performance is shown via total portfolio value over time.

8. **Conversation-history cap** (§9) — the chat prompt includes at most the last 20 messages (~10 exchanges).

9. **Structured-output fallback** (§9 *Structured Output Reliability*) — verify strict structured outputs on the model/provider early; otherwise fall back to JSON + schema-validate + one retry. The backend always validates before auto-executing trades.

10. **Money precision** (§8) — cash, price, and `avg_cost` are rounded to cents at trade execution.

11. **SSE is the source of truth for live prices** (§10 *Technical Notes*) — REST price fields are initial-paint snapshots only; the frontend does not poll them for live updates.

12. **Backend owns the core** (§3 *Core Principle*) — the server is authoritative for all state and computation (valuation, P&L, change %, price history); the frontend is a thin rendering layer. Chosen for multi-user scalability (the cache/history layer is the seam to a shared store like Redis), server-side security/validation, and cross-client consistency, without sacrificing speed (fast inference + in-memory caches + SSE).
