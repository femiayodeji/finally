"""Portfolio valuation and trade execution — the authoritative money math (PLAN §8).

Every trade — manual (`POST /api/portfolio/trade`) or LLM-issued (`app.llm`) —
goes through `execute_trade`, so validation and ledger math live in exactly
one place.
"""

from __future__ import annotations

from app import db
from app.market import MarketDataSource, PriceCache

from .errors import TradeError

_QTY_EPSILON = 1e-9


def get_portfolio(cache: PriceCache) -> dict:
    """Current positions, cash balance, total value, unrealized P&L.

    Valuation is computed server-side from the live price cache — the
    frontend never derives these numbers itself (PLAN §3). A position whose
    ticker has no cached price yet (freshly opened, priced next tick) values
    at its own `avg_cost` so P&L reads as zero rather than crashing.
    """
    cash_balance = db.get_cash_balance()
    positions_out = []
    positions_value = 0.0
    total_unrealized_pnl = 0.0

    for position in db.list_positions():
        ticker = position["ticker"]
        quantity = position["quantity"]
        avg_cost = position["avg_cost"]
        current_price = cache.get_price(ticker)
        if current_price is None:
            current_price = avg_cost

        market_value = round(quantity * current_price, 2)
        unrealized_pnl = round(quantity * (current_price - avg_cost), 2)
        unrealized_pnl_percent = (
            round((current_price - avg_cost) / avg_cost * 100, 2) if avg_cost else 0.0
        )

        positions_value += market_value
        total_unrealized_pnl += unrealized_pnl
        positions_out.append(
            {
                "ticker": ticker,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_percent": unrealized_pnl_percent,
            }
        )

    positions_value = round(positions_value, 2)
    return {
        "cash_balance": round(cash_balance, 2),
        "positions_value": positions_value,
        "total_value": round(cash_balance + positions_value, 2),
        "total_unrealized_pnl": round(total_unrealized_pnl, 2),
        "positions": positions_out,
    }


def snapshot_portfolio(cache: PriceCache) -> float:
    """Compute total portfolio value, persist a snapshot, and return the value."""
    total_value = get_portfolio(cache)["total_value"]
    db.insert_snapshot(total_value)
    return total_value


async def execute_trade(
    cache: PriceCache,
    source: MarketDataSource,
    ticker: str,
    side: str,
    quantity: float,
) -> dict:
    """Execute a market order: instant fill at the current cached price.

    Validates inputs, applies the ledger math from PLAN §8 (weighted average
    cost on buy, unchanged avg_cost on sell, position row deleted at qty 0,
    money rounded to cents), records the trade + a snapshot, and keeps the
    market-data tracked set (watchlist ∪ open positions) in sync. Raises
    `TradeError` — and changes nothing — on any validation failure.
    """
    ticker = ticker.upper()
    side = side.lower()
    if side not in ("buy", "sell"):
        raise TradeError(f"Invalid side '{side}': must be 'buy' or 'sell'")
    if quantity is None or quantity <= 0:
        raise TradeError("Quantity must be positive")

    price = cache.get_price(ticker)
    if price is None:
        raise TradeError(f"No price available for {ticker}")

    existing = db.get_position(ticker)
    cash_balance = db.get_cash_balance()

    if side == "buy":
        cost = round(quantity * price, 2)
        if cost > cash_balance:
            raise TradeError(
                f"Insufficient cash: need ${cost:.2f}, have ${cash_balance:.2f}"
            )
        if existing:
            new_quantity = existing["quantity"] + quantity
            new_avg_cost = (
                existing["quantity"] * existing["avg_cost"] + quantity * price
            ) / new_quantity
        else:
            new_quantity = quantity
            new_avg_cost = price
        db.upsert_position(ticker, new_quantity, round(new_avg_cost, 2))
        db.set_cash_balance(round(cash_balance - cost, 2))
        await source.add_ticker(ticker)
    else:
        held = existing["quantity"] if existing else 0.0
        if not existing or held + _QTY_EPSILON < quantity:
            raise TradeError(f"Insufficient shares: requested {quantity}, hold {held}")
        proceeds = round(quantity * price, 2)
        new_quantity = held - quantity
        db.set_cash_balance(round(cash_balance + proceeds, 2))
        if new_quantity <= _QTY_EPSILON:
            db.delete_position(ticker)
            if not db.is_watchlisted(ticker):
                await source.remove_ticker(ticker)
        else:
            db.upsert_position(ticker, new_quantity, existing["avg_cost"])

    trade = db.insert_trade(ticker, side, quantity, price)
    snapshot_portfolio(cache)
    return {"trade": trade, "portfolio": get_portfolio(cache)}
