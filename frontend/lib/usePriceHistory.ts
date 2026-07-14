"use client";

import { useEffect, useRef, useState } from "react";
import { getPriceHistory } from "./api";
import type { PricePoint, PriceUpdate } from "./types";

const MAX_POINTS = 600; // mirrors the backend's ring buffer (PLAN.md §6)

/** Backfills a ticker's price series from `/api/prices/{ticker}/history` on
 * mount/ticker change, then extends it live as SSE ticks arrive for that
 * ticker — "sparklines render populated, then keep growing" (PLAN.md §2,
 * §10). The series itself is always backend data; nothing here is derived. */
export function usePriceHistory(ticker: string | null, latest: PriceUpdate | undefined): PricePoint[] {
  const [points, setPoints] = useState<PricePoint[]>([]);
  const lastTimestamp = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    lastTimestamp.current = null;
    // Reset on ticker change before kicking off the backfill fetch — see
    // PortfolioContext.tsx for why this is exempted from
    // react-hooks/set-state-in-effect rather than restructured.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPoints([]);
    if (!ticker) return;
    getPriceHistory(ticker)
      .then((res) => {
        if (cancelled) return;
        setPoints(res.history);
        lastTimestamp.current = res.history.at(-1)?.timestamp ?? null;
      })
      .catch(() => {
        // Backfill is a nice-to-have; an empty-then-growing series is a fine fallback.
      });
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  useEffect(() => {
    if (!latest || latest.timestamp === lastTimestamp.current) return;
    lastTimestamp.current = latest.timestamp;
    setPoints((prev) => {
      const next = [...prev, { timestamp: latest.timestamp, price: latest.price }];
      return next.length > MAX_POINTS ? next.slice(next.length - MAX_POINTS) : next;
    });
  }, [latest]);

  return points;
}
