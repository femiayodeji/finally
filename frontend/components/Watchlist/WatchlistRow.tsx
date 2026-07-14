"use client";

import { useEffect, useRef, useState } from "react";
import { useTickerPrice } from "@/lib/PriceStreamContext";
import { usePriceHistory } from "@/lib/usePriceHistory";
import { directionColorClass, formatCurrency, formatPercent } from "@/lib/format";
import type { WatchlistEntry } from "@/lib/types";
import { Sparkline } from "./Sparkline";

interface WatchlistRowProps {
  initial: WatchlistEntry;
  selected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

export function WatchlistRow({ initial, selected, onSelect, onRemove }: WatchlistRowProps) {
  const ticker = initial.ticker;
  // SSE supersedes the REST snapshot the moment a tick arrives; until then
  // the row shows the initial-paint values from GET /api/watchlist.
  const live = useTickerPrice(ticker);
  const history = usePriceHistory(ticker, live);

  const price = live?.price ?? initial.price;
  const changePercent = live?.session_change_percent ?? initial.session_change_percent;
  const direction = live?.direction ?? initial.direction;

  // Flash on every price change (PLAN.md §2). Remounting the overlay via an
  // incrementing key restarts the CSS animation reliably on each tick.
  const [flashId, setFlashId] = useState(0);
  const [flashDirection, setFlashDirection] = useState<"up" | "down" | null>(null);
  const lastPrice = useRef<number | null>(null);

  useEffect(() => {
    if (price == null) return;
    if (lastPrice.current !== null && price !== lastPrice.current) {
      setFlashDirection(price > lastPrice.current ? "up" : "down");
      setFlashId((id) => id + 1);
    }
    lastPrice.current = price;
  }, [price]);

  const positive = (changePercent ?? 0) >= 0;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(ticker)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onSelect(ticker);
      }}
      data-testid="watchlist-row"
      data-ticker={ticker}
      className={`group relative flex cursor-pointer items-center justify-between gap-3 overflow-hidden border-b border-line-soft px-3 py-2 ${
        selected ? "bg-elevated" : "hover:bg-panel-alt"
      }`}
    >
      <Sparkline points={history} positive={positive} className="opacity-60" />
      {flashDirection && (
        <div
          key={flashId}
          data-testid="price-flash"
          className={`pointer-events-none absolute inset-0 ${
            flashDirection === "up" ? "flash-up" : "flash-down"
          }`}
        />
      )}

      <span className="relative z-10 font-data text-sm font-medium text-ink">{ticker}</span>

      <div className="relative z-10 flex items-center gap-3">
        <div className="flex flex-col items-end">
          <span className="font-data text-sm text-ink">{price != null ? formatCurrency(price) : "—"}</span>
          <span className={`font-data text-xs ${directionColorClass(direction)}`}>
            {changePercent != null ? formatPercent(changePercent) : "—"}
          </span>
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove(ticker);
          }}
          className="px-1 text-xs text-ink-faint opacity-0 transition-opacity hover:text-down group-hover:opacity-100"
          aria-label={`Remove ${ticker} from watchlist`}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
