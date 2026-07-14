"""Application configuration.

Loads `.env` from the project root and exposes the environment-variable
contract from `planning/PLAN.md` §5 / `planning/BUILD_PLAN.md` §3.

`DB_PATH` mirrors what `app.db.connection.get_db_path()` resolves (same
`FINALLY_DB_PATH` env var, same default) so both modules agree on where the
SQLite file lives without either importing the other.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/app/config.py -> parents[2] is the project root (finally/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
MASSIVE_API_KEY: str = os.environ.get("MASSIVE_API_KEY", "")
LLM_MOCK: bool = os.environ.get("LLM_MOCK", "false").strip().lower() in ("1", "true", "yes")

_DEFAULT_DB_PATH = str(PROJECT_ROOT / "db" / "finally.db")
DB_PATH: str = os.environ.get("FINALLY_DB_PATH", _DEFAULT_DB_PATH)
