"use client";

import { useEffect, useRef } from "react";
import {
  ColorType,
  LineSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import type { Direction, PricePoint } from "@/lib/types";

const COLOR_BY_DIRECTION: Record<Direction, string> = {
  up: "#3fb950", // positive
  down: "#f85149", // negative
  flat: "#8b949e", // neutral
};

/** Minimal ~60x24px sparkline (no axes/gridlines/crosshair), colored by
 * direction (01-UI-SPEC.md "Watchlist panel"). The chart/series are created
 * once in a ref and updated via `setData` as `points` grows — this is a
 * consumer of `usePriceHistory`'s already-backfilled-then-live series, not a
 * reimplementation of it (PLAN.md §6/§10). Disposed on unmount to bound
 * per-row memory (threat T-05-02). */
export function Sparkline({
  points,
  direction,
}: {
  points: PricePoint[];
  direction: Direction | null | undefined;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      width: 60,
      height: 24,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "transparent",
        attributionLogo: false,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      crosshair: {
        vertLine: { visible: false, labelVisible: false },
        horzLine: { visible: false, labelVisible: false },
      },
      rightPriceScale: { visible: false },
      timeScale: { visible: false },
      handleScroll: false,
      handleScale: false,
    });

    const series = chart.addSeries(LineSeries, {
      color: COLOR_BY_DIRECTION[direction ?? "flat"],
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
    // Chart/series are created once per mount; direction/points updates below
    // reuse the same instances rather than recreating them.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    series.applyOptions({ color: COLOR_BY_DIRECTION[direction ?? "flat"] });
  }, [direction]);

  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart) return;
    series.setData(
      points.map((p) => ({ time: p.timestamp as UTCTimestamp, value: p.price }) as { time: Time; value: number }),
    );
    chart.timeScale().fitContent();
  }, [points]);

  return <div ref={containerRef} className="h-6 w-[60px] shrink-0" />;
}
