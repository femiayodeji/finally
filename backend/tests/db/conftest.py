"""Fixtures for db package tests — every test gets its own temp SQLite file."""

from __future__ import annotations

import pytest

from app.db import init_db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Point FINALLY_DB_PATH at a fresh temp file and initialize (schema + seed)."""
    db_file = tmp_path / "test_finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_file))
    init_db()
    return db_file
