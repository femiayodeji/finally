"use client";

import { useEffect, useRef, type MouseEvent } from "react";
import { useTickerPrice } from "@/lib/PriceStreamContext";
import { usePriceHistory } from "@/lib/usePriceHistory";
import { useWatchlist } from "@/lib/WatchlistContext";
import { useSelectedTicker } from "@/lib/SelectedTickerContext";
import { directionColorClass, formatCurrency, formatPercent } from "@/lib/format";
import type { Direction, WatchlistEntry } from "@/lib/types";
import { Sparkline } from "./Sparkline";

// 25% opacity of the locked positive/negative tokens (01-UI-SPEC.md "Watchlist
// panel" price-flash spec) — fades to transparent over 500ms ease-out below.
const FLASH_COLOR: Record<"up" | "down", string> = {
  up: "rgba(63, 185, 80, 0.25)",
  down: "rgba(248, 81, 73, 0.25)",
};

/** One 40px watchlist row: ticker, backfilled+growing sparkline, live price
 * over server session_change_percent, click-to-select, hover-to-remove
 * (01-UI-SPEC.md "Watchlist panel"). Live values come from `useTickerPrice`
 * (the SSE frame) once the stream delivers a tick for this ticker; until
 * then the row falls back to the REST initial-paint snapshot carried on
 * `entry` (PLAN.md §10) — SSE is the sole source of truth after mount
 * (UI-10), REST is initial paint only. */
export function WatchlistRow({ entry }: { entry: WatchlistEntry }) {
  const { ticker } = entry;
  const live = useTickerPrice(ticker);
  const points = usePriceHistory(ticker, live);
  const { remove } = useWatchlist();
  const { selected, setSelected } = useSelectedTicker();

  const price = live?.price ?? entry.price;
  const sessionChangePercent = live?.session_change_percent ?? entry.session_change_percent;
  const sparklineDirection: Direction | null = live?.direction ?? entry.direction;
  // session_change_percent (not tick direction) drives the price/% text
  // color, per D-07 — a flat tick can still sit on a positive/negative session.
  const changeDirection: Direction =
    sessionChangePercent == null ? "flat" : sessionChangePercent > 0 ? "up" : sessionChangePercent < 0 ? "down" : "flat";

  const flashRef = useRef<HTMLDivElement | null>(null);
  const lastFlashedTimestamp = useRef<number | null>(null);

  useEffect(() => {
    if (!live || live.timestamp === lastFlashedTimestamp.current) return;
    lastFlashedTimestamp.current = live.timestamp;
    if (live.direction === "flat") return;
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      // Reduced motion: rely on text color only, skip the background transition entirely.
      return;
    }
    const el = flashRef.current;
    if (!el) return;
    el.style.transition = "none";
    el.style.backgroundColor = FLASH_COLOR[live.direction];
    // Force a reflow so the transition below animates from the flash color
    // instead of being coalesced with the style write above.
    void el.offsetHeight;
    el.style.transition = "background-color 500ms ease-out";
    el.style.backgroundColor = "transparent";
  }, [live]);

  const isSelected = selected === ticker;

  const handleRemove = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    void remove(ticker);
  };

  return (
    <div
      onClick={() => setSelected(ticker)}
      className={`group relative flex h-10 shrink-0 cursor-pointer items-center gap-2 border-l-[3px] px-3 ${
        isSelected ? "border-accent-blue bg-accent-blue/[0.08]" : "border-transparent"
      }`}
    >
      <div ref={flashRef} className="pointer-events-none absolute inset-0" />
      <span className="z-10 w-12 shrink-0 truncate text-sm font-semibold">{ticker}</span>
      <Sparkline points={points} direction={sparklineDirection} />
      <div className="z-10 ml-auto flex flex-col items-end">
        <span className="numeric text-sm">{price != null ? formatCurrency(price) : "—"}</span>
        <span className={`numeric text-xs ${directionColorClass(changeDirection)}`}>
          {sessionChangePercent != null ? formatPercent(sessionChangePercent) : "—"}
        </span>
      </div>
      <button
        type="button"
        aria-label={`Remove ${ticker} from watchlist`}
        onClick={handleRemove}
        className="absolute right-0 top-1/2 z-20 flex h-11 w-11 -translate-y-1/2 items-center justify-center bg-panel text-sm text-neutral opacity-0 transition-opacity duration-150 hover:text-negative focus-visible:opacity-100 group-hover:opacity-100"
      >
        ×
      </button>
    </div>
  );
}
