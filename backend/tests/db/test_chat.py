"""Tests for the chat_messages repository."""

from __future__ import annotations

import time

from app.db import insert_message, recent_messages


class TestChatRepository:
    """Unit tests for chat message insert/recall, including the 20-message cap."""

    def test_insert_message_returns_full_row(self):
        """Test insert_message() returns id, created_at, and echoes role/content."""
        message = insert_message("user", "What's my portfolio worth?")
        assert message["id"]
        assert message["created_at"]
        assert message["role"] == "user"
        assert message["content"] == "What's my portfolio worth?"
        assert message["actions"] is None

    def test_actions_round_trip_through_json(self):
        """Test a dict passed as `actions` survives the JSON store/parse round-trip."""
        actions = {"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}]}
        insert_message("assistant", "Bought 10 AAPL.", actions=actions)
        [message] = recent_messages()
        assert message["actions"] == actions

    def test_recent_messages_chronological(self):
        """Test recent_messages() returns oldest first."""
        insert_message("user", "first")
        time.sleep(0.002)
        insert_message("assistant", "second")
        time.sleep(0.002)
        insert_message("user", "third")
        contents = [m["content"] for m in recent_messages()]
        assert contents == ["first", "second", "third"]

    def test_recent_messages_capped_at_limit(self):
        """Test recent_messages() caps at `limit`, keeping the most recent (default 20)."""
        for i in range(25):
            insert_message("user", f"message {i}")
            time.sleep(0.001)
        messages = recent_messages(limit=20)
        assert len(messages) == 20
        assert messages[-1]["content"] == "message 24"
        assert messages[0]["content"] == "message 5"

    def test_messages_scoped_per_user(self):
        """Test chat history is isolated per user_id."""
        insert_message("user", "hello", user_id="alice")
        assert recent_messages() == []
        assert len(recent_messages(user_id="alice")) == 1
