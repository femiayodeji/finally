"""Repository for `chat_messages` — conversation history with the LLM."""

from __future__ import annotations

import json
from uuid import uuid4

from .connection import get_connection
from .util import now_iso


def insert_message(
    role: str, content: str, actions: dict | None = None, user_id: str = "default"
) -> dict:
    """Insert a chat message and return the full row.

    `actions` (trades/watchlist changes executed alongside an assistant reply)
    is stored as JSON text; None for user messages.
    """
    message_id = str(uuid4())
    created_at = now_iso()
    actions_json = json.dumps(actions) if actions is not None else None
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, user_id, role, content, actions_json, created_at),
        )
    return {
        "id": message_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "actions": actions,
        "created_at": created_at,
    }


def recent_messages(limit: int = 20, user_id: str = "default") -> list[dict]:
    """Return the user's most recent messages, chronological (oldest first).

    `actions` is parsed back from JSON into a dict (None if it wasn't set).
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content, actions, created_at FROM (
                SELECT role, content, actions, created_at FROM chat_messages
                WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
            ) ORDER BY created_at ASC
            """,
            (user_id, limit),
        ).fetchall()
        return [
            {
                "role": row["role"],
                "content": row["content"],
                "actions": json.loads(row["actions"]) if row["actions"] else None,
                "created_at": row["created_at"],
            }
            for row in rows
        ]
