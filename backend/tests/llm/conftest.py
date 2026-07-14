"""Fixtures for `app.llm` tests.

`app/services/` is owned by another agent and built in parallel; these
fixtures let `app.llm.service`'s lazy `from app.services.* import ...` calls
succeed regardless of whether that package exists yet or what it currently
contains, by stubbing it in `sys.modules`.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db import init_db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Point FINALLY_DB_PATH at a fresh temp file and initialize (schema + seed)."""
    db_file = tmp_path / "test_finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_file))
    init_db()
    return db_file


@pytest.fixture
def fake_services(monkeypatch):
    """Stub `app.services.{portfolio_service,watchlist_service,errors}`.

    Returns a namespace of the stub modules so tests can set return values
    and assert on call args, independent of the real service layer landing.
    """
    portfolio_mod = types.ModuleType("app.services.portfolio_service")
    portfolio_mod.get_portfolio = MagicMock(
        return_value={"cash_balance": 10000.0, "positions": [], "total_value": 10000.0}
    )
    portfolio_mod.execute_trade = AsyncMock(return_value={"trade": {}, "portfolio": {}})

    watchlist_mod = types.ModuleType("app.services.watchlist_service")
    watchlist_mod.get_watchlist = MagicMock(return_value=[])
    watchlist_mod.add_to_watchlist = AsyncMock(return_value={"ticker": "PYPL"})
    watchlist_mod.remove_from_watchlist = AsyncMock(return_value=None)

    errors_mod = types.ModuleType("app.services.errors")

    class TradeError(Exception):
        pass

    class WatchlistError(Exception):
        pass

    errors_mod.TradeError = TradeError
    errors_mod.WatchlistError = WatchlistError

    monkeypatch.setitem(sys.modules, "app.services", types.ModuleType("app.services"))
    monkeypatch.setitem(sys.modules, "app.services.portfolio_service", portfolio_mod)
    monkeypatch.setitem(sys.modules, "app.services.watchlist_service", watchlist_mod)
    monkeypatch.setitem(sys.modules, "app.services.errors", errors_mod)

    return types.SimpleNamespace(portfolio=portfolio_mod, watchlist=watchlist_mod, errors=errors_mod)
