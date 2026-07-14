"""Tests for the connection helper."""

from __future__ import annotations

from pathlib import Path

from app.db.connection import get_connection, get_db_path


class TestConnection:
    """Unit tests for DB path resolution and the connection context manager."""

    def test_get_db_path_honors_env_override(self, monkeypatch, tmp_path):
        """Test FINALLY_DB_PATH, when set, wins over the default path."""
        custom = tmp_path / "custom.db"
        monkeypatch.setenv("FINALLY_DB_PATH", str(custom))
        assert get_db_path() == str(custom)

    def test_get_db_path_default_falls_under_project_root_db_dir(self, monkeypatch):
        """Test the fallback (no env var) resolves to <project_root>/db/finally.db."""
        monkeypatch.delenv("FINALLY_DB_PATH", raising=False)
        path = Path(get_db_path())
        assert path.name == "finally.db"
        assert path.parent.name == "db"

    def test_connection_creates_parent_directory(self, monkeypatch, tmp_path):
        """Test get_connection() creates the db file's parent dir if missing."""
        nested = tmp_path / "nested" / "dir" / "finally.db"
        monkeypatch.setenv("FINALLY_DB_PATH", str(nested))
        with get_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
        assert nested.exists()

    def test_connection_row_factory_allows_name_access(self):
        """Test rows from get_connection() are accessible by column name."""
        with get_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
            conn.execute("INSERT INTO t (x) VALUES (42)")
            row = conn.execute("SELECT x FROM t").fetchone()
        assert row["x"] == 42

    def test_connection_rolls_back_on_exception(self):
        """Test a write is not committed if the block raises."""
        with get_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS t2 (x INTEGER)")

        try:
            with get_connection() as conn:
                conn.execute("INSERT INTO t2 (x) VALUES (1)")
                raise ValueError("boom")
        except ValueError:
            pass

        with get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM t2").fetchone()
        assert row["n"] == 0
