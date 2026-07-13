# FinAlly — AI Trading Workstation

A visually stunning, AI-powered trading workstation: stream live market data, trade a simulated portfolio, and chat with an LLM copilot that can analyze positions and execute trades from natural language. Think Bloomberg terminal with an AI assistant.

Built entirely by coding agents as the capstone project for an agentic AI coding course.

## Vision

- **Live price streaming** via SSE, with green/red flash animations and sparklines
- **Simulated portfolio** — $10k virtual cash, market orders, instant fills, no fees
- **Portfolio visualizations** — treemap heatmap, P&L chart, positions table
- **AI chat assistant** — analyzes holdings, suggests trades, and auto-executes them
- **Watchlist management** — track tickers manually or via the AI
- **Dark, data-dense terminal aesthetic**

## Architecture

A single Docker container serves everything on port 8000:

- **Backend** — FastAPI (Python / `uv`), owns all state and computation (valuation, P&L, change %, price history), streams prices over SSE
- **Frontend** — Next.js (TypeScript, Tailwind) built as a static export, served by FastAPI
- **Database** — SQLite, initialized and seeded on startup, volume-mounted for persistence
- **Market data** — built-in GBM simulator by default, or Massive (Polygon.io) API when a key is provided
- **AI** — LiteLLM → OpenRouter (`openai/gpt-oss-120b` via Cerebras) with structured outputs

The full specification lives in [`planning/PLAN.md`](planning/PLAN.md).

## Status

🚧 **In progress.** The **market-data subsystem** is complete, tested, and reviewed
([summary](planning/MARKET_DATA_SUMMARY.md)): a unified `MarketDataSource` interface with a
correlated-GBM simulator and a Massive REST poller, feeding a thread-safe in-memory price cache
and an SSE endpoint (73 passing tests, 84% coverage). The portfolio, watchlist, chat, database,
frontend, and Docker packaging are still to be built.

## Development

```bash
cd backend
uv sync

# Run the tests
uv run pytest

# See the market data engine live (Rich terminal demo)
uv run market_data_demo.py
```

## Environment Variables

Create a `.env` in the project root:

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes (for chat) | OpenRouter API key for the AI assistant |
| `MASSIVE_API_KEY` | No | Massive (Polygon.io) key for real market data; omit to use the simulator |
| `LLM_MOCK` | No | Set `true` for deterministic mock LLM responses (testing) |

## Project Structure

```
finally/
├── backend/     # FastAPI uv project (market data built; rest in progress)
├── planning/    # Project spec (PLAN.md) and agent contracts
└── db/          # SQLite volume mount target (runtime)
```

## License

See [LICENSE](LICENSE).
