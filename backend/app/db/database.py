"""SQLite persistence layer: connection helper, schema init, and seed data.

Uses the stdlib `sqlite3` module only (no new dependency, PLAN.md §7). The
database is initialized on app startup — before the market-data background
task starts — so the tracked ticker set always has a populated watchlist to
read (PLAN.md §7 "DB Initialized on Startup").
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.market.seed_prices import SEED_PRICES

# Resolved to the top-level `db/finally.db` volume mount target (PLAN.md §4,
# §11). Env-overridable so tests (and alternate deployments) can point at a
# tmp path without touching the real database file.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_DEFAULT_DB_PATH = _PROJECT_ROOT / "db" / "finally.db"

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0


def get_db_path() -> Path:
    """Resolve the SQLite file path, honoring the FINALLY_DB_PATH override."""
    override = os.environ.get("FINALLY_DB_PATH", "").strip()
    return Path(override) if override else _DEFAULT_DB_PATH


def get_connection() -> sqlite3.Connection:
    """Open a connection to the SQLite database.

    Rows are returned as `sqlite3.Row` (dict-like access by column name).
    Creates the parent directory if it doesn't exist yet (first run against
    a fresh Docker volume, DB-03).
    """
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't already exist (DB-01).

    Idempotent via `CREATE TABLE IF NOT EXISTS` in schema.sql — safe to call
    on every startup, including against an already-initialized database.
    """
    schema_sql = _SCHEMA_PATH.read_text()
    with get_connection() as conn:
        conn.executescript(schema_sql)


def seed_default_data() -> None:
    """Insert the default user profile and the 10 default watchlist tickers.

    Uses `INSERT OR IGNORE` so re-seeding an already-populated database is a
    no-op (DB-02 idempotency). The ticker list is read from
    `app.market.seed_prices.SEED_PRICES` — the single source of truth for
    the default watchlist (shared with the simulator).
    """
    now = datetime.now(UTC).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at)
            VALUES (?, ?, ?)
            """,
            (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
        )
        for ticker in SEED_PRICES:
            conn.execute(
                """
                INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now),
            )


def initialize() -> None:
    """Run schema creation then seeding. Call once at app startup (APP startup order)."""
    init_db()
    seed_default_data()


def get_tracked_tickers(user_id: str = DEFAULT_USER_ID) -> list[str]:
    """Return the union of watchlist tickers and open-position tickers.

    This is the tracked ticker set the market-data source must start with
    (PLAN.md §6 "Tracked Ticker Set" — watchlist ∪ open positions, not the
    watchlist alone).
    """
    with get_connection() as conn:
        watchlist_rows = conn.execute(
            "SELECT DISTINCT ticker FROM watchlist WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        position_rows = conn.execute(
            "SELECT DISTINCT ticker FROM positions WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    tracked = {row["ticker"] for row in watchlist_rows}
    tracked.update(row["ticker"] for row in position_rows)
    return sorted(tracked)
