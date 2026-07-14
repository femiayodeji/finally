"""AI chat assistant — LLM integration for FinAlly (PLAN §9).

Public surface: `from app.llm import create_chat_router`. The backend lead
mounts this in `app.main` (BUILD_PLAN §2/§7). The router itself lives in
`app.api.chat` per the ownership table (BUILD_PLAN §1), re-exported here so
callers don't need to know that detail.
"""

from __future__ import annotations

from app.api.chat import create_chat_router

from .schema import ChatResponse, Trade, WatchlistChange
from .service import handle_chat

__all__ = [
    "create_chat_router",
    "handle_chat",
    "ChatResponse",
    "Trade",
    "WatchlistChange",
]
