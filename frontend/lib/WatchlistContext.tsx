"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { addToWatchlist, getWatchlist, removeFromWatchlist } from "./api";
import type { WatchlistEntry } from "./types";

interface WatchlistContextValue {
  entries: WatchlistEntry[];
  loading: boolean;
  error: string | null;
  add: (ticker: string) => Promise<void>;
  remove: (ticker: string) => Promise<void>;
  /** Resyncs the ticker list from the server. Exposed so callers outside
   * this module — namely chat, which can add/remove watchlist entries
   * through the LLM's own code path (PLAN.md §9) — can refresh the panel
   * after actions the panel itself didn't initiate. */
  refresh: () => Promise<void>;
}

const WatchlistContext = createContext<WatchlistContextValue>({
  entries: [],
  loading: true,
  error: null,
  add: async () => {},
  remove: async () => {},
  refresh: async () => {},
});

/** `GET /api/watchlist` supplies the ticker list plus an initial-paint price
 * snapshot (PLAN.md §10) — the row components take over from SSE the moment
 * the stream delivers a tick for that ticker. */
export function WatchlistProvider({ children }: { children: React.ReactNode }) {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await getWatchlist();
      setEntries(res.watchlist);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // See PortfolioContext.tsx for why this deliberate fetch-on-mount call
    // is exempted from react-hooks/set-state-in-effect rather than restructured.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

  const add = useCallback(
    async (ticker: string) => {
      await addToWatchlist(ticker.trim().toUpperCase());
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (ticker: string) => {
      // Removing a ticker still held as a position keeps it tracked
      // server-side (PLAN.md §6) but drops off this list either way.
      setEntries((prev) => prev.filter((e) => e.ticker !== ticker));
      try {
        await removeFromWatchlist(ticker);
      } finally {
        await refresh();
      }
    },
    [refresh],
  );

  return (
    <WatchlistContext.Provider value={{ entries, loading, error, add, remove, refresh }}>
      {children}
    </WatchlistContext.Provider>
  );
}

export function useWatchlist(): WatchlistContextValue {
  return useContext(WatchlistContext);
}
