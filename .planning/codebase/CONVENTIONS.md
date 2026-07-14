# Coding Conventions

**Analysis Date:** 2026-07-14

## Naming Patterns

**Files:**
- Python: `snake_case.py` (e.g., `cache.py`, `simulator.py`, `factory.py`)
- TypeScript: `camelCase.ts` or `PascalCase.tsx` (e.g., `api.ts`, `types.ts`, `PriceStreamContext.tsx`)
- Test files: `test_*.py` for Python (pytest convention)

**Functions & Methods:**
- Python: `snake_case` (e.g., `update()`, `get_price()`, `to_dict()`)
- TypeScript: `camelCase` (e.g., `formatCurrency()`, `toDate()`, `usePriceHistory()`)
- Private methods: prefix with `_` in both languages (e.g., `_add_ticker_internal()`, `_rebuild_cholesky()`)

**Variables:**
- Python: `snake_case` (e.g., `event_probability`, `z_correlated`, `inFlight` becomes `in_flight`)
- TypeScript: `camelCase` (e.g., `disconnectTimer`, `inFlight`, `lastTimestamp`)
- Private/internal attributes: prefix with `_` (e.g., `_prices`, `_lock`, `_tickers`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `TRADING_SECONDS_PER_YEAR`, `DEFAULT_DT`, `DISCONNECTED_AFTER_MS`, `MAX_POINTS`)

**Types & Classes:**
- Python: `PascalCase` (e.g., `PriceUpdate`, `PriceCache`, `MarketDataSource`, `GBMSimulator`)
- TypeScript: `PascalCase` for types, interfaces, and components (e.g., `Direction`, `PriceStreamFrame`, `PriceStreamProvider`)
- Type aliases: `PascalCase` (e.g., `TradeSide`, `WatchlistAction`)

## Code Style

**Formatting:**
- **Backend:** Ruff formatter (enforced)
  - Line length: 100 characters
  - Linting rules: E (errors), F (pyFlakes), I (isort imports), N (pep8-naming), W (warnings)
  - E501 (line too long) ignored — handled by formatter
- **Frontend:** Assumed Prettier or similar (not explicitly configured in repo)
  - TypeScript/React files use standard spacing

**Linting:**
- **Backend (Ruff):** `ruff check app/ tests/` validates naming, imports, and style
- **Frontend:** No eslint config found in repo; conventions followed from Next.js defaults

## Import Organization

**Backend (Python):**
- Order followed (enforced by `I` in ruff):
  1. `from __future__ import annotations` (always first)
  2. Standard library imports (`import os`, `import asyncio`, `import logging`)
  3. Third-party imports (`import numpy as np`, `import pytest`)
  4. Local imports (`from .cache import PriceCache`, `from .interface import MarketDataSource`)
- Example from `simulator.py`:
  ```python
  from __future__ import annotations
  
  import asyncio
  import logging
  import math
  import random
  
  import numpy as np
  
  from .cache import PriceCache
  from .interface import MarketDataSource
  from .seed_prices import SEED_PRICES, TICKER_PARAMS
  ```

**Frontend (TypeScript):**
- Order observed:
  1. React imports (`import { createContext, useContext, ... } from "react"`)
  2. Type imports (`import type { PriceUpdate } from "./types"`)
  3. Local function imports (`import { getPortfolio } from "./api"`)
- Example from `PriceStreamContext.tsx`:
  ```typescript
  import { createContext, useContext, useEffect, useRef, useState } from "react";
  import type { PriceStreamFrame, PriceUpdate } from "./types";
  ```

## Error Handling

**Python:**
- Graceful degradation: skip malformed data instead of crashing (e.g., in `MassiveDataSource._poll_once()`, skip snapshots that lack `last_trade`)
- Network errors caught and logged; cache state unchanged (e.g., if Massive API fails, poller continues on next cycle)
- Custom error classes extend `Error` where semantics matter (backend doesn't show examples yet)

**TypeScript:**
- Try/catch with fallback (e.g., `getPriceHistory()` catches backfill failures; empty-then-growing series is acceptable)
- Custom error class `ApiRequestError` extends `Error` with `status` property in `api.ts`
- JSON parsing wrapped in try/catch; malformed SSE frames are skipped, last good prices remain on screen
- Error messages propagated to UI state (e.g., `error: string | null` in context values)

## Logging

**Framework:** Python's `logging` module via `logger = logging.getLogger(__name__)`

**Patterns:**
- Factory creates logger per module (e.g., `logger = logging.getLogger(__name__)` in `factory.py`)
- Info level for lifecycle events (e.g., "Market data source: Massive API (real data)" in `factory.py`)
- Scope: used for operational events (startup, data source selection), not verbose tracing

**TypeScript:** No logging framework observed; errors/status handled via context state and UI display

## Comments

**When to Comment:**
- Non-obvious mathematical logic (e.g., GBM formula and time-step explanation in `simulator.py`)
- Architectural decisions and trade-offs (e.g., "this is the hot path — called every 500ms. Keep it fast" in `simulator.py:74`)
- Links to specification (`PLAN.md §3`, `PLAN.md §6`) when implementing spec requirements
- Clarifying why a code pattern is chosen (e.g., "This is a deliberate fetch-on-mount-then-poll" in `PortfolioContext.tsx`)

**JSDoc/TSDoc:**
- All public class/function definitions include docstrings
- Format: one-line summary followed by multi-line explanation if needed
- Parameters and return types documented in docstrings
- Example from `cache.py`:
  ```python
  def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
      """Record a new price for a ticker. Returns the created PriceUpdate.
      
      Automatically computes direction and change from the previous price.
      If this is the first update for the ticker, previous_price == price (direction='flat').
      """
  ```

## Function Design

**Size:** Prefer small, focused functions (20–40 lines typical)

**Parameters:** 
- Type hints required for all parameters (Python: `ticker: str`, TypeScript: `ticker: string`)
- Default values used for optional configuration (e.g., `timestamp: float | None = None`, `digits = 2`)

**Return Values:**
- Type hints required (e.g., `-> PriceUpdate`, `-> Promise<Portfolio>`)
- Immutable returns preferred (e.g., `PriceUpdate` is a frozen dataclass)
- None used explicitly for absent values (Python: `float | None`, TypeScript: `number | null`)

## Module Design

**Exports:**
- Python: Import by name from module (e.g., `from app.market import PriceCache, create_market_data_source`)
- TypeScript: Named exports for functions and types; default export not used for components (e.g., `export function PriceStreamProvider(...)`, `export type Direction = ...`)

**Barrel Files:** Not observed in this codebase

**Dataclasses & Immutability (Python):**
- Frozen dataclasses used for immutable value objects (e.g., `@dataclass(frozen=True, slots=True)` on `PriceUpdate`)
- Slots enable memory efficiency and prevent accidental attribute additions
- Properties used for derived values (e.g., `change`, `change_percent`, `direction` as properties on `PriceUpdate`)

## Dunder Methods

**Python:**
- Implement `__len__`, `__contains__` for collection-like classes (e.g., `PriceCache.__len__()`, `PriceCache.__contains__()`)
- Makes classes Pythonic and support `len()`, `in` operators

## Type Safety

**Python:**
- `from __future__ import annotations` enables forward references
- Union syntax: `float | None` (not `Optional[float]`)
- Generics: `dict[str, float]` (not `Dict[str, float]`)
- All public functions have type hints

**TypeScript:**
- Strict null checking implicit (React/Next.js config)
- Union types for constrained strings: `type Direction = "up" | "down" | "flat"`
- Interfaces for API contracts: `interface PriceUpdate { ... }`
- Type imports used where possible: `import type { ... } from "./types"`

## Comments & Architectural Links

**Referential comments:** Point to `planning/PLAN.md` sections for architectural context. Examples:
- `// Backend owns the numbers (§3)` in `format.ts`
- `// SSE is the source of truth for live prices (PLAN.md §10)` in `api.ts`
- `// Type hints enable multi-user scaling later (§3)` pattern

---

*Convention analysis: 2026-07-14*
