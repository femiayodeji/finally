"use client";

import { useEffect, useRef } from "react";
import { AreaSeries, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { useTickerPrice } from "@/lib/PriceStreamContext";
import { usePriceHistory } from "@/lib/usePriceHistory";
import { directionColorClass, formatCurrency, formatPercent } from "@/lib/format";
import { Panel } from "../ui/Panel";

/** Larger detail chart for the selected ticker. Backfills from
 * `/api/prices/{ticker}/history` and extends live from SSE (PLAN.md §10) —
 * `usePriceHistory` owns that data flow; this component only renders it. */
export function MainChart({ ticker }: { ticker: string | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  const live = useTickerPrice(ticker ?? "");
  const points = usePriceHistory(ticker, live);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { color: "transparent" },
        textColor: "#8b96a5",
        // Canvas rendering can't resolve CSS custom properties, so the
        // literal family name is used here (next/font loads the same face).
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "#1a212b" },
        horzLines: { color: "#1a212b" },
      },
      rightPriceScale: { borderColor: "#232b37" },
      timeScale: { borderColor: "#232b37", timeVisible: true, secondsVisible: false },
    });
    const series = chart.addSeries(AreaSeries, {
      lineColor: "#209dd7",
      topColor: "rgba(32, 157, 215, 0.28)",
      bottomColor: "rgba(32, 157, 215, 0)",
      lineWidth: 2,
      priceLineVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;
    seriesRef.current.setData(
      points.map((p) => ({ time: p.timestamp as UTCTimestamp, value: p.price })),
    );
  }, [points]);

  const price = live?.price;
  const changePercent = live?.session_change_percent;
  const direction = live?.direction;

  return (
    <Panel
      title="Chart"
      className="h-full"
      action={
        ticker ? (
          <div className="flex items-baseline gap-2">
            <span className="font-data text-sm font-medium text-ink">{ticker}</span>
            {price != null && (
              <span className="font-data text-sm text-ink">{formatCurrency(price)}</span>
            )}
            {changePercent != null && (
              <span className={`font-data text-xs ${directionColorClass(direction)}`}>
                {formatPercent(changePercent)}
              </span>
            )}
          </div>
        ) : null
      }
    >
      <div className="relative h-full min-h-[280px] w-full">
        <div ref={containerRef} className="h-full w-full" />
        {!ticker && (
          <div className="absolute inset-0 flex items-center justify-center bg-panel font-body text-sm text-ink-faint">
            Select a ticker to view its chart
          </div>
        )}
      </div>
    </Panel>
  );
}
