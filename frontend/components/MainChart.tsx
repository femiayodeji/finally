"use client";

import { useEffect, useRef } from "react";
import {
  AreaSeries,
  ColorType,
  CrosshairMode,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { PricePoint } from "@/lib/types";

// Locked tokens (01-UI-SPEC.md "Main chart panel"): accent-blue line + area
// gradient fading to transparent over a transparent (bg-canvas-inheriting)
// background; faint gridlines; neutral axis text at Label size.
const LINE_COLOR = "#209dd7";
const AREA_TOP_COLOR = "rgba(32, 157, 215, 0.35)";
const AREA_BOTTOM_COLOR = "rgba(32, 157, 215, 0)";
const AXIS_TEXT_COLOR = "#8b949e";
const GRID_LINE_COLOR = "rgba(48, 54, 61, 0.35)"; // border-muted at low opacity
const BORDER_COLOR = "#30363d";

/** TradingView Lightweight Charts filled-area line series for the main
 * detail chart (01-UI-SPEC.md "Main chart panel", T-06-01). The chart
 * instance and series are created once in a ref and disposed on unmount;
 * `points` is plotted exactly as given via `setData` on every change so the
 * chart renders populated immediately (history backfill) and grows in place
 * as `usePriceHistory` appends live SSE ticks — no client-side derivation or
 * smoothing (PLAN.md §3, UI-10 owned by Plan 05). */
export function MainChart({ points }: { points: PricePoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: AXIS_TEXT_COLOR,
        fontSize: 12,
        fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, sans-serif",
      },
      grid: {
        vertLines: { color: GRID_LINE_COLOR },
        horzLines: { color: GRID_LINE_COLOR },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: BORDER_COLOR },
      timeScale: { borderColor: BORDER_COLOR, timeVisible: true, secondsVisible: false },
      autoSize: true,
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: LINE_COLOR,
      topColor: AREA_TOP_COLOR,
      bottomColor: AREA_BOTTOM_COLOR,
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
    const series = seriesRef.current;
    if (!series) return;
    series.setData(
      points.map((point) => ({
        time: point.timestamp as UTCTimestamp,
        value: point.price,
      })),
    );
    chartRef.current?.timeScale().fitContent();
  }, [points]);

  return <div ref={containerRef} className="h-full w-full" />;
}
