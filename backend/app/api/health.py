"""Health check endpoint (PLAN.md §8)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe for Docker/deployment.

    Deliberately does not touch the DB or price cache — stays a cheap,
    always-answerable check (APP-04).
    """
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}
