"use client";

import { useEffect, useRef, useState } from "react";
import { useTickerPrice } from "@/lib/PriceStreamContext";
import { useSelectedTicker } from "@/lib/SelectedTickerContext";
import { usePriceHistory } from "@/lib/usePriceHistory";
import { useWatchlist } from "@/lib/WatchlistContext";
import { formatCurrency, formatPercent } from "@/lib/format";
import { Panel } from "./Panel";
import { MainChart } from "./MainChart";

/** Replaces the Plan 03 placeholder: wires `SelectedTickerContext` (set by
 * watchlist row clicks in Plan 05) to the filled-area detail chart, auto-
 * selects the first watchlist ticker on load so the chart is never empty,
 * and renders the live symbol/price/session-change-% header readout
 * (01-UI-SPEC.md "Main chart panel"). */
export function MainChartPanel() {
  const { selected, setSelected } = useSelectedTicker();
  const { entries, loading } = useWatchlist();
  const tick = useTickerPrice(selected ?? "");
  const points = usePriceHistory(selected, tick);

  // Auto-select the first watchlist ticker on load, only while nothing is
  // selected yet — once set, watchlist row clicks (Plan 05) own selection.
  useEffect(() => {
    if (selected === null && entries.length > 0) {
      setSelected(entries[0].ticker);
    }
  }, [selected, entries, setSelected]);

  // Price-flash mechanics mirroring the watchlist rows (01-UI-SPEC.md
  // "Watchlist panel" flash spec): brief tinted background on each tick that
  // fades to transparent over 500ms; `motion-safe:` keeps the tint entirely
  // out of the DOM under prefers-reduced-motion, leaving only the price/
  // change-% text color to communicate direction.
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const prevPriceRef = useRef<number | null>(null);

  useEffect(() => {
    // Selection changed — the next tick for the new ticker isn't a "change"
    // from the old one's price.
    prevPriceRef.current = null;
    setFlash(null);
  }, [selected]);

  useEffect(() => {
    if (!tick) return;
    if (prevPriceRef.current !== null && tick.price !== prevPriceRef.current && tick.direction !== "flat") {
      setFlash(tick.direction);
    }
    prevPriceRef.current = tick.price;
  }, [tick]);

  useEffect(() => {
    if (!flash) return;
    const timer = setTimeout(() => setFlash(null), 500);
    return () => clearTimeout(timer);
  }, [flash]);

  if (!loading && entries.length === 0) {
    return (
      <Panel className="h-full w-full items-center justify-center text-center">
        <h3 className="text-lg font-semibold text-neutral">No chart to show</h3>
        <p className="mt-1 max-w-xs text-xs text-neutral opacity-70">
          Add a ticker to your watchlist to see its chart.
        </p>
      </Panel>
    );
  }

  const isChartLoading = selected === null || points.length === 0;
  const flashBgClass =
    flash === "up" ? "motion-safe:bg-positive/25" : flash === "down" ? "motion-safe:bg-negative/25" : "";
  const pillClass =
    tick?.direction === "up"
      ? "bg-positive/15 text-positive"
      : tick?.direction === "down"
        ? "bg-negative/15 text-negative"
        : "bg-neutral/15 text-neutral";

  return (
    <Panel className="h-full w-full">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-lg font-semibold">{selected ?? ""}</h2>
        <div className="flex items-center gap-3">
          <span
            className={`numeric rounded px-1 text-3xl font-semibold transition-colors duration-500 ease-out motion-reduce:transition-none ${flashBgClass}`}
          >
            {tick ? formatCurrency(tick.price) : "—"}
          </span>
          <span className={`numeric rounded-full px-2 py-0.5 text-xs ${pillClass}`}>
            {tick ? formatPercent(tick.session_change_percent) : "—"}
          </span>
        </div>
      </div>
      <div className="relative mt-3 min-h-0 flex-1">
        {isChartLoading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-xs text-neutral">Loading chart…</p>
          </div>
        )}
        {selected && <MainChart points={points} />}
      </div>
    </Panel>
  );
}
