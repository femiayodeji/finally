# Testing Patterns

**Analysis Date:** 2026-07-14

## Test Framework

**Runner:**
- pytest 8.3.0+
- Config: `backend/pyproject.toml` `[tool.pytest.ini_options]`

**Assertion Library:**
- pytest assertions (no additional library; Python's `assert` is sufficient)

**Run Commands:**
```bash
uv run --extra dev pytest -v              # Run all tests with verbose output
uv run --extra dev pytest --cov=app       # Run with coverage report
uv run --extra dev ruff check app/ tests/ # Lint code
```

## Test File Organization

**Location:**
- Python tests co-located in `backend/tests/` directory tree mirroring `backend/app/`
- Test files named `test_*.py` (pytest convention)
- Structure: `backend/tests/market/` contains tests for `backend/app/market/`

**Naming:**
- Test modules: `test_*.py` (e.g., `test_cache.py`, `test_simulator.py`, `test_factory.py`)
- Test classes: `Test*` prefix (e.g., `TestPriceCache`, `TestGBMSimulator`, `TestFactory`)
- Test methods: `test_*` prefix (e.g., `test_update_and_get()`, `test_prices_are_positive()`)

**Directory Structure:**
```
backend/
├── app/
│   └── market/
│       ├── cache.py
│       ├── simulator.py
│       ├── models.py
│       └── ...
├── tests/
│   ├── conftest.py
│   ├── __init__.py
│   └── market/
│       ├── __init__.py
│       ├── test_cache.py
│       ├── test_simulator.py
│       ├── test_factory.py
│       └── ...
└── pyproject.toml
```

## Test Structure

**Suite Organization:**
```python
class TestPriceCache:
    """Unit tests for the PriceCache."""

    def test_update_and_get(self):
        """Test updating and getting a price."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.ticker == "AAPL"
        assert update.price == 190.50
        assert cache.get("AAPL") == update
```

**Patterns:**
- One assertion per test method when focused on a single behavior
- Multiple related assertions acceptable if testing a single outcome
- Setup in the test method or via fixtures (see below)
- Clear, descriptive test method names that document intent

## Mocking

**Framework:** `unittest.mock` from Python standard library

**Patterns:**
```python
from unittest.mock import MagicMock, patch

# Mock environment variables
with patch.dict(os.environ, {"MASSIVE_API_KEY": "test-key"}, clear=True):
    source = create_market_data_source(cache)

# Mock method return values
with patch.object(source, "_fetch_snapshots", return_value=mock_snapshots):
    await source._poll_once()

# Mock exceptions
with patch.object(source, "_fetch_snapshots", side_effect=Exception("network error")):
    await source._poll_once()  # Should not raise
```

**What to Mock:**
- External APIs (e.g., Massive client's `_fetch_snapshots()`)
- Environment variables (e.g., `MASSIVE_API_KEY`)
- Slow or non-deterministic operations (e.g., network calls, timers)

**What NOT to Mock:**
- Core business logic (e.g., `PriceCache.update()`, `GBMSimulator.step()`)
- Internal implementation details (test the public interface)
- Simple utility functions

## Fixtures and Factories

**Test Data:**
- Helper functions for creating mock objects: `_make_snapshot()` in `test_massive.py`
  ```python
  def _make_snapshot(ticker: str, price: float, timestamp_ms: int) -> MagicMock:
      """Create a mock Massive snapshot object."""
      snap = MagicMock()
      snap.ticker = ticker
      snap.last_trade = MagicMock()
      snap.last_trade.price = price
      snap.last_trade.timestamp = timestamp_ms
      return snap
  ```

**Location:**
- conftest.py: `backend/tests/conftest.py`
- Shared fixtures: pytest fixtures defined in conftest.py (available to all tests)
- Example: `event_loop_policy` fixture for async test support

## Coverage

**Requirements:** No explicit coverage threshold enforced (100% not required)

**View Coverage:**
```bash
uv run --extra dev pytest --cov=app --cov-report=term-missing
```

**Excluded lines:** (from `pyproject.toml`)
- `pragma: no cover`
- `def __repr__`
- `raise AssertionError`
- `raise NotImplementedError`
- `if __name__ == .__main__.:` (main guard)
- `if TYPE_CHECKING:` (type-checking imports)

## Test Types

**Unit Tests:**
- Scope: Single class or function in isolation
- Approach: Direct instantiation, mock external dependencies
- Examples: `TestPriceCache`, `TestGBMSimulator`, `TestFactory`
- Location: `backend/tests/market/test_*.py`

**Integration Tests:**
- Scope: Multiple components working together (e.g., `SimulatorDataSource` + `PriceCache`)
- Approach: Minimal mocking; use real implementations where reasonable
- Async tests: Mark with `@pytest.mark.asyncio`
- Examples: `TestSimulatorDataSource` in `test_simulator_source.py` — tests that `start()` populates cache, prices update over time, `stop()` is clean
- Location: Same directory as unit tests; distinguished by test class name or method patterns

**E2E Tests:**
- Framework: Playwright (not yet implemented in codebase)
- Location: `test/` directory
- Config: Would use `docker-compose.test.yml` to spin up app + browser
- Environment: `LLM_MOCK=true` for deterministic results

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
class TestSimulatorDataSource:
    """Integration tests for SimulatorDataSource."""

    async def test_start_populates_cache(self):
        """Test that start() immediately populates the cache."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])
        
        assert cache.get("AAPL") is not None
        assert cache.get("GOOGL") is not None
        
        await source.stop()
```

**State Evolution:**
```python
def test_direction_up(self):
    """Test price update with upward direction."""
    cache = PriceCache()
    cache.update("AAPL", 190.00)  # First update (flat direction)
    update = cache.update("AAPL", 191.00)  # Second update (up direction)
    assert update.direction == "up"
    assert update.change == 1.00
```

**Edge Cases:**
```python
def test_remove_nonexistent_is_noop(self):
    """Test that removing a non-existent ticker is a no-op."""
    cache = PriceCache()
    cache.remove("AAPL")  # Should not raise

def test_add_duplicate_is_noop(self):
    """Test that adding a duplicate ticker is a no-op."""
    sim = GBMSimulator(tickers=["AAPL"])
    sim.add_ticker("AAPL")
    assert len(sim._tickers) == 1
```

**Boundary Conditions:**
```python
def test_price_rounding(self):
    """Test that prices are rounded to 2 decimal places."""
    cache = PriceCache()
    update = cache.update("AAPL", 190.12345)
    assert update.price == 190.12

def test_unknown_ticker_gets_random_seed_price(self):
    """Test that unknown tickers get random seed prices."""
    sim = GBMSimulator(tickers=["ZZZZ"])
    price = sim.get_price("ZZZZ")
    assert price is not None
    assert 50.0 <= price <= 300.0
```

**Error Handling:**
```python
async def test_api_error_does_not_crash(self):
    """Test that API errors don't crash the poller."""
    cache = PriceCache()
    source = MassiveDataSource(
        api_key="test-key",
        price_cache=cache,
        poll_interval=60.0,
    )
    source._tickers = ["AAPL"]
    source._client = MagicMock()

    with patch.object(source, "_fetch_snapshots", side_effect=Exception("network error")):
        await source._poll_once()  # Should not raise

    assert cache.get_price("AAPL") is None  # No update happened
```

**Temporal/Timing Tests:**
```python
async def test_prices_update_over_time(self):
    """Test that prices are updated periodically."""
    cache = PriceCache()
    source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
    await source.start(["AAPL"])

    initial_version = cache.version
    await asyncio.sleep(0.3)  # Several update cycles

    # Version should have incremented (prices updated)
    assert cache.version > initial_version

    await source.stop()
```

## Test Docstrings

All test methods have docstrings describing what they test:

```python
def test_first_update_is_flat(self):
    """Test that the first update has flat direction."""
    cache = PriceCache()
    update = cache.update("AAPL", 190.50)
    assert update.direction == "flat"
    assert update.previous_price == 190.50
```

Format: one-line summary of the test's intent (what behavior is being verified).

## Frontend Testing Notes

**Status:** No automated test suite observed in codebase yet

**Expected patterns (when implemented):**
- Framework: React Testing Library or Vitest
- Contexts tested via mock providers (examples in CONVENTIONS.md show exported contexts for this purpose)
- Components tested with mock data, not real API calls
- Hooks tested via renderHook or similar utilities
- Integration tests: React Testing Library with user-centric queries

---

*Testing analysis: 2026-07-14*
