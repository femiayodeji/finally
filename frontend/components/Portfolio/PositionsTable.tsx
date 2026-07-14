"use client";

import { usePortfolio } from "@/lib/PortfolioContext";
import { formatCurrency, formatPercent, formatQuantity } from "@/lib/format";
import { Panel } from "../ui/Panel";

const HEADERS = ["Ticker", "Qty", "Avg Cost", "Price", "P&L", "% Chg"];

export function PositionsTable() {
  const { portfolio, loading } = usePortfolio();
  const positions = portfolio?.positions ?? [];

  return (
    <Panel title="Positions" className="h-full" bodyClassName="overflow-auto">
      {positions.length === 0 ? (
        <div className="flex h-full min-h-[120px] items-center justify-center font-body text-sm text-ink-faint">
          {loading ? "Loading…" : "No open positions"}
        </div>
      ) : (
        <table className="w-full border-collapse font-data text-xs">
          <thead className="sticky top-0 bg-panel">
            <tr className="border-b border-line-soft text-left text-ink-faint">
              {HEADERS.map((h, i) => (
                <th
                  key={h}
                  className={`px-3 py-1.5 font-body font-normal uppercase tracking-wide ${i > 0 ? "text-right" : ""}`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={p.ticker} data-testid="position-row" className="border-b border-line-soft/60 hover:bg-panel-alt">
                <td className="px-3 py-1.5 text-ink">{p.ticker}</td>
                <td className="px-3 py-1.5 text-right text-ink-dim">{formatQuantity(p.quantity)}</td>
                <td className="px-3 py-1.5 text-right text-ink-dim">{formatCurrency(p.avg_cost)}</td>
                <td className="px-3 py-1.5 text-right text-ink">{formatCurrency(p.current_price)}</td>
                <td className={`px-3 py-1.5 text-right ${p.unrealized_pnl >= 0 ? "text-up" : "text-down"}`}>
                  {formatCurrency(p.unrealized_pnl)}
                </td>
                <td className={`px-3 py-1.5 text-right ${p.unrealized_pnl_percent >= 0 ? "text-up" : "text-down"}`}>
                  {formatPercent(p.unrealized_pnl_percent)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
