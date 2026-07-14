# Technology Stack

**Analysis Date:** 2026-07-14

## Languages

**Primary:**
- Python 3.12+ - Backend server logic, market data simulation, portfolio computation
- TypeScript - Frontend application (React components)
- SQL - SQLite database schema and queries

**Secondary:**
- Bash - Deployment scripts (shell wrappers for Docker)
- PowerShell - Deployment scripts (Windows)

## Runtime

**Environment:**
- Python 3.12+ (enforced by `pyproject.toml`)
- Node.js 20+ (frontend build, not deployed to container)

**Package Manager:**
- `uv` (Python) - Replacement for pip/venv; fast, deterministic, lockfile-based
- `npm` (Node.js) - Frontend dependencies (built, not yet cataloged; `node_modules` present)

**Lockfiles:**
- `backend/uv.lock` - Present, pinned Python dependencies
- `frontend/package-lock.json` - Not found; frontend not yet scaffolded with package.json in repo root

## Frameworks

**Core:**
- FastAPI 0.115.0+ - Async web server, REST API, SSE streaming endpoints
- Uvicorn 0.32.0+ - ASGI server (HTTP + WebSocket, though SSE is one-way)
- Starlette - HTTP utilities (FastAPI's underlying library)
- Pydantic 2.x - Request/response validation, type checking

**Frontend:**
- Next.js - React framework for static export (build target: `output: 'export'`)
- React - UI components (implicit via Next.js)
- Tailwind CSS - Utility-first styling (configured but no config file found; may be in .next)

**Testing:**
- pytest 8.3.0+ - Test runner for backend
- pytest-asyncio 0.24.0+ - Async test support
- pytest-cov 5.0.0+ - Coverage reporting
- React Testing Library or Jest - Frontend tests (not yet scaffolded)

**Build/Dev:**
- ruff 0.7.0+ - Fast Python linter and formatter (replaces flake8/black)
- Hatchling - Python package builder (via `[build-system]` in pyproject.toml)
- Rich 13.0.0+ - Terminal output formatting (used in market data demo)

## Key Dependencies

**Critical:**
- `fastapi` 0.115.0+ - Core web framework for all REST endpoints and SSE
- `uvicorn[standard]` 0.32.0+ - Production ASGI server with all extras (uvloop, httptools)
- `numpy` 2.0.0+ - Numerical computation for GBM simulator (Cholesky decomposition, random variates)
- `massive` 1.0.0+ - Polygon.io REST client for real market data (optional at runtime; environment-gated)
- `pydantic` 2.x - Data validation via FastAPI integration

**Infrastructure:**
- `python-dotenv` - Loads `.env` file for `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`
- `rich` 13.0.0+ - Colored terminal output; used in `market_data_demo.py`
- `httptools`, `uvloop` - Performance optimizations bundled via `uvicorn[standard]`
- `typing-extensions` - Type hints backports for Python 3.12 compatibility

**Testing (dev-only):**
- `pytest` 8.3.0+ - Test framework
- `pytest-asyncio` 0.24.0+ - Async test fixtures
- `pytest-cov` 5.0.0+ - Coverage measurement

## Configuration

**Environment:**
- `.env` (project root, gitignored) - Runtime configuration:
  - `OPENROUTER_API_KEY` (required for chat) - OpenRouter API credentials
  - `MASSIVE_API_KEY` (optional) - Polygon.io key; if absent, uses built-in simulator
  - `LLM_MOCK` (optional, testing) - Set `true` for deterministic mock LLM responses
- No `.env.example` or documentation of env vars committed to repo; see `planning/PLAN.md` for reference

**Build:**
- `backend/pyproject.toml` - Python project metadata, dependencies, dev extras, tool configuration
  - `[tool.ruff]` - Linter rules: line length 100, target Python 3.12
  - `[tool.pytest.ini_options]` - Test discovery, asyncio mode configuration
  - `[tool.coverage.run]` - Coverage settings, source path
- `backend/uv.lock` - Frozen dependency tree (v1, pinned)
- No `tsconfig.json`, `next.config.js`, or `tailwind.config.ts` found in frontend root (likely in `.next/build`)

**Database:**
- SQLite schema + seed logic not yet implemented (placeholder: `planning/PLAN.md` describes intended schema)
- Volume mount target: `db/` directory at project root (persists `finally.db` across container restarts)

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js 20+ (frontend build only)
- `uv` package manager (not pip/venv)
- Docker (for containerized deployment)

**Production:**
- Docker container serving on port 8000
- Single process (no process manager like Gunicorn; Uvicorn runs directly)
- SQLite filesystem with persistent volume mount
- No external databases or caches yet (in-memory price cache in backend)

## Docker & Deployment

**Containerization:**
- Multi-stage Dockerfile (planned, not yet committed) per `PLAN.md`:
  1. Stage 1: Node 20 slim → build frontend static export
  2. Stage 2: Python 3.12 slim → install uv, run `uv sync`, copy frontend build, expose 8000, CMD uvicorn
- Volume: `finally-data:/app/db` (SQLite persistence)
- Port: 8000 (single origin for frontend + all API routes)

**Dependency Versions:**
- Base: Python 3.12 slim Docker image
- Node: 20 slim (build stage only)
- uvicorn: `0.32.0+` with `[standard]` extras (includes uvloop, httptools)

---

*Stack analysis: 2026-07-14*
