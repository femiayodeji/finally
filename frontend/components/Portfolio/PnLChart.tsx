"use client";

import { useEffect, useRef, useState } from "react";
import { LineSeries, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { getPortfolioHistory } from "@/lib/api";
import { toDate } from "@/lib/format";
import type { PortfolioSnapshot } from "@/lib/types";
import { Panel } from "../ui/Panel";

// portfolio_snapshots are recorded every 30s (or immediately after a trade,
// PLAN.md §7) — polling a little faster than that keeps the line current
// without hammering the endpoint.
const POLL_INTERVAL_MS = 15000;

/** Total portfolio value over time, from `portfolio_snapshots` (PLAN.md §10). */
export function PnLChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      getPortfolioHistory()
        .then((res) => {
          if (!cancelled) setSnapshots(res.history);
        })
        .catch(() => {
          // keep showing the last good series on a transient failure
        });
    };
    load();
    const id = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { color: "transparent" },
        textColor: "#8b96a5",
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
    const series = chart.addSeries(LineSeries, {
      color: "#ecad0a",
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
      snapshots.map((s) => ({
        time: (toDate(s.recorded_at).getTime() / 1000) as UTCTimestamp,
        value: s.total_value,
      })),
    );
  }, [snapshots]);

  return (
    <Panel title="Portfolio Value" className="h-full">
      <div ref={containerRef} className="h-full min-h-[160px] w-full" />
    </Panel>
  );
}
