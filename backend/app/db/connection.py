"""SQLite connection helper.

Uses a short-lived connection per operation rather than a pooled/shared one —
simple, safe across FastAPI's async event loop plus background threads (the
market-data task and the 30s snapshot task), and cheap enough for SQLite.

The DB Engineer doesn't own `app/config.py` (Backend API Engineer's area). Until
that module exposes `DB_PATH`, the path is read directly from the
`FINALLY_DB_PATH` env var here, falling back to `<project_root>/db/finally.db`.
Tests monkeypatch `FINALLY_DB_PATH` to point at a temp file, so the path is
resolved fresh on every call rather than cached at import time.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# backend/app/db/connection.py -> parents[3] is the project root (finally/)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DB_PATH = _PROJECT_ROOT / "db" / "finally.db"


def get_db_path() -> str:
    """Resolve the SQLite file path, honoring `FINALLY_DB_PATH` if set."""
    return os.environ.get("FINALLY_DB_PATH", str(_DEFAULT_DB_PATH))


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a connection for a single operation, committing on success.

    Row access is by name (`sqlite3.Row`); WAL mode allows concurrent readers
    alongside a writer; foreign keys are enforced (off by default in sqlite3).
    """
    path = Path(get_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
