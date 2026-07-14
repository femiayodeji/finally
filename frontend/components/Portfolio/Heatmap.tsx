"use client";

import { ResponsiveContainer, Treemap } from "recharts";
import { usePortfolio } from "@/lib/PortfolioContext";
import { formatPercent } from "@/lib/format";
import { Panel } from "../ui/Panel";

const UP_RGB = "63, 185, 80";
const DOWN_RGB = "248, 81, 73";

/** Heat intensity scales with |P&L %|, clamped at +/-10% so one runaway
 * winner/loser doesn't wash out the rest of the map. */
function heatColor(pnlPercent: number): string {
  const clamped = Math.max(-10, Math.min(10, pnlPercent));
  const alpha = 0.12 + (Math.abs(clamped) / 10) * 0.55;
  return `rgba(${clamped >= 0 ? UP_RGB : DOWN_RGB}, ${alpha.toFixed(2)})`;
}

interface CellProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  pnlPercent?: number;
}

function TreemapCell({ x = 0, y = 0, width = 0, height = 0, name = "", pnlPercent = 0 }: CellProps) {
  if (width < 2 || height < 2) return null;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={heatColor(pnlPercent)} stroke="#0d1117" strokeWidth={1} />
      {width > 46 && height > 28 && (
        <text x={x + 6} y={y + 16} fontFamily="JetBrains Mono, monospace" fontSize={11} fill="#e6edf3">
          {name}
        </text>
      )}
      {width > 46 && height > 44 && (
        <text
          x={x + 6}
          y={y + 32}
          fontFamily="JetBrains Mono, monospace"
          fontSize={10}
          fill={pnlPercent >= 0 ? "#3fb950" : "#f85149"}
        >
          {formatPercent(pnlPercent)}
        </text>
      )}
    </g>
  );
}

/** Positions sized by weight, colored by P&L (PLAN.md §2/§10). */
export function Heatmap() {
  const { portfolio, loading } = usePortfolio();
  const positions = portfolio?.positions ?? [];

  const data = positions.map((p) => ({
    name: p.ticker,
    size: Math.max(p.market_value, 0.01),
    pnlPercent: p.unrealized_pnl_percent,
  }));

  return (
    <Panel title="Positions Heatmap" className="h-full">
      {data.length === 0 ? (
        <div className="flex h-full min-h-[160px] items-center justify-center font-body text-sm text-ink-faint">
          {loading ? "Loading…" : "No open positions"}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%" minHeight={160}>
          <Treemap
            data={data}
            dataKey="size"
            stroke="#0d1117"
            isAnimationActive={false}
            content={<TreemapCell />}
          />
        </ResponsiveContainer>
      )}
    </Panel>
  );
}
