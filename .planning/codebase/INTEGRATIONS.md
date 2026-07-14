# External Integrations

**Analysis Date:** 2026-07-14

## APIs & External Services

**Market Data (Environment-Gated):**
- **Massive API (Polygon.io)** - Real-time and historical market data
  - Used by: `backend/app/market/massive_client.py` (`MassiveDataSource`)
  - Activation: Set `MASSIVE_API_KEY` environment variable (non-empty)
  - Fallback: If key is absent/empty, built-in GBM simulator is used
  - SDK/Client: `massive` package v1.0.0+
  - REST polling: Requests tickers on configurable interval (e.g., every 15 sec for free tier)
  - Auth: Bearer token via `MASSIVE_API_KEY` env var
  - Response format: Parsed into `PriceUpdate` dataclass (ticker, price, previous_price, timestamp)

**LLM Chat (Planned, Not Yet Implemented):**
- **OpenRouter** - Proxy to open-source LLM via Cerebras inference
  - Planned usage: `backend/app/chat/` (not yet created)
  - Model: `openrouter/openai/gpt-oss-120b` (120B parameter model, via Cerebras)
  - Client library: LiteLLM (declared in PLAN.md, not yet in pyproject.toml)
  - Auth: `OPENROUTER_API_KEY` environment variable
  - Request format: Structured outputs (JSON schema) for parsing trades and watchlist actions
  - Async: Will use async LiteLLM client
  - Status: Integration is documented in `planning/PLAN.md` §9; implementation pending

## Data Storage

**Databases:**
- **SQLite** - Single-file, embedded relational database
  - Location: `db/finally.db` (volume-mounted at container runtime)
  - Schema: Not yet created (placeholder schema in `planning/PLAN.md` §7)
  - Client: Python `sqlite3` module (standard library) or similar ORM (to be chosen)
  - Initialization: Lazy on first backend request (create tables + seed data if missing)
  - Tables (planned):
    - `users_profile` - User cash balance, ID
    - `watchlist` - Watched tickers per user
    - `positions` - Current holdings per ticker
    - `trades` - Trade history (append-only log)
    - `portfolio_snapshots` - Portfolio value time series (for P&L chart)
    - `chat_messages` - Conversation history with LLM

**File Storage:**
- **Local filesystem** - No external blob storage
  - Static frontend assets served by FastAPI from `backend/static/` (built Next.js output)
  - SQLite file persists via Docker volume

**Caching:**
- **In-Memory** - Price cache (no external cache service)
  - `backend/app/market/cache.py` (`PriceCache` class)
  - Holds latest price, previous price, timestamp per ticker
  - Thread-safe via `threading.Lock`
  - Bounded rolling history: ~600 price points (~5 minutes at 500ms intervals) per ticker
  - Resets on restart (not persisted to SQLite)
  - Planned future: Redis or Memcached for multi-user horizontal scaling

## Authentication & Identity

**Auth Provider:**
- **None / Mock** - No authentication implemented
  - Single hardcoded user: `user_id="default"` in database schema
  - All database queries filter by this constant
  - Future multi-user: Requires auth layer (OAuth2, JWT, etc.; not in scope)

**API Keys:**
- `OPENROUTER_API_KEY` - OpenRouter authentication (for LLM chat, planned)
- `MASSIVE_API_KEY` - Polygon.io authentication (optional, for real market data)

## Monitoring & Observability

**Error Tracking:**
- None detected - No integration with Sentry, DataDog, or similar

**Logging:**
- **Python `logging` module** - Standard library logger
  - Used in: `backend/app/market/factory.py`, likely elsewhere
  - Format: Not configured (defaults to console output)
  - Levels: INFO (market data source selection), likely DEBUG/WARNING elsewhere
  - Production: Logs go to stdout (suitable for Docker container log aggregation)

**Traces/Metrics:**
- None detected - No OpenTelemetry, Prometheus, or APM integration

## CI/CD & Deployment

**Hosting:**
- **Docker** - Container runtime (planned)
  - Single container on port 8000
  - No docker-compose for production (single service)
  - Optional: Cloud platforms (AWS App Runner, Render, Heroku) per `PLAN.md` §11

**CI Pipeline:**
- **GitHub Actions** - Workflows may exist in `.github/workflows/` (not explored in detail)
- No detected: GitLab CI, CircleCI, Jenkins

**Build Artifacts:**
- Dockerfile (planned, not yet committed) - Multi-stage build
- uv.lock - Python dependency lock
- Next.js static export in `frontend/out/` - Pre-built, checked into repo or generated at container build time

## Environment Configuration

**Required env vars:**
- `OPENROUTER_API_KEY` - LLM chat functionality (when implemented)

**Optional env vars:**
- `MASSIVE_API_KEY` - Real market data source; if empty, use simulator
- `LLM_MOCK` - Set `true` for deterministic mock LLM responses (testing/demo)

**Secrets location:**
- `.env` file (gitignored) at project root
- No secret manager integration (HashiCorp Vault, AWS Secrets Manager, etc.)
- Mounted into container via Docker `--env-file .env` flag or similar

## Webhooks & Callbacks

**Incoming:**
- None detected - No webhook endpoints for external services to call

**Outgoing:**
- None detected - No callbacks to external systems (yet)
- Planned: LLM chat auto-executes trades (internal trade execution, not outbound)

## Data Flow & Service Boundaries

**Startup Flow:**
```
Docker start
  └─ Backend (Python 3.12 slim)
      ├─ Load .env → env vars
      ├─ Initialize SQLite (lazy on first request)
      │   └─ Create schema + seed 10 default tickers
      ├─ Create PriceCache (in-memory)
      ├─ create_market_data_source()
      │   ├─ Check MASSIVE_API_KEY
      │   ├─ If set → MassiveDataSource (Polygon.io REST poller)
      │   └─ If empty → SimulatorDataSource (GBM simulator)
      ├─ Start market data task (polls/simulates ~500ms)
      │   └─ Update PriceCache
      ├─ Serve FastAPI app on :8000
      │   ├─ GET /api/stream/prices → SSE stream (PriceCache → browser)
      │   ├─ POST /api/portfolio/trade → Validate + execute (trades table)
      │   ├─ POST /api/chat → LLM call (planned) → Trade validation
      │   └─ /* → Static frontend files
```

**Runtime Data Sources (Priority):**
1. **PriceCache** (in-memory) - Current source of truth for all price data
2. **SQLite (planned)** - Persistent state (trades, portfolio snapshots, watchlist, chat history)
3. **Massive API (optional)** - External market data (if key provided)
4. **OpenRouter (planned)** - External LLM inference (if key provided and not mocked)

---

*Integration audit: 2026-07-14*
