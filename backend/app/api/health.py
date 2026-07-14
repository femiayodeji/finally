"""Health check endpoint (for Docker/deployment)."""

from __future__ import annotations

from fastapi import APIRouter


def create_health_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["health"])

    @router.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return router
