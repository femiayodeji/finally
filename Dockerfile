# syntax=docker/dockerfile:1
#
# FinAlly — single-container build (PLAN.md §11).
# Stage 1 builds the Next.js static export. Stage 2 installs the Python
# backend with uv and bundles the export as the static files it serves.

# ---------------------------------------------------------------------------
# Stage 1: Next.js static export
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Copy lockfiles first so `npm ci` is cached unless dependencies change.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build
# Next.js `output: 'export'` (PLAN.md §10) writes the static site to /frontend/out

# ---------------------------------------------------------------------------
# Stage 2: Python backend (uv-managed) + bundled static frontend
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS backend

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies first (cached layer, only invalidated by lockfile changes)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy application source and install the project itself
# (README.md is required at build time — pyproject.toml's `readme` field points to it)
COPY backend/app ./app
COPY backend/README.md ./README.md
RUN uv sync --frozen --no-dev

# Bundle the frontend static export where the backend serves it from (/app/static)
COPY --from=frontend-builder /frontend/out ./static

# Run as a non-root user; /app/db is the volume mount point for the SQLite file
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/db \
    && chown -R appuser:appuser /app
USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FINALLY_DB_PATH=/app/db/finally.db

EXPOSE 8000
VOLUME ["/app/db"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
