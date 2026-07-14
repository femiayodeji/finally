"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getPortfolio } from "./api";
import type { Portfolio } from "./types";

const POLL_INTERVAL_MS = 4000;

interface PortfolioContextValue {
  portfolio: Portfolio | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const PortfolioContext = createContext<PortfolioContextValue>({
  portfolio: null,
  loading: true,
  error: null,
  refresh: async () => {},
});

/** Polls `GET /api/portfolio` on an interval. Valuation and P&L are computed
 * server-side (PLAN.md §3) — polling, rather than recomputing totals from
 * SSE prices in the client, is how the header's "live" total value stays
 * current without the frontend deriving core numbers itself. `refresh()`
 * lets a trade or chat action push an immediate update instead of waiting
 * for the next tick. */
export function PortfolioProvider({ children }: { children: React.ReactNode }) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const data = await getPortfolio();
      setPortfolio(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load portfolio");
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Deliberate fetch-on-mount-then-poll: a single kickoff call, not a
    // loop or a render-driven derivation, so it doesn't cause the cascading
    // re-renders this rule guards against. useEffectEvent doesn't actually
    // exempt this (the linter still treats its wrapped function as a
    // setState call), and there's no external store to subscribe to here —
    // just a REST endpoint — so useSyncExternalStore doesn't apply either.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
    const id = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <PortfolioContext.Provider value={{ portfolio, loading, error, refresh }}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio(): PortfolioContextValue {
  return useContext(PortfolioContext);
}

// Exported (rather than kept module-private) so tests can render components
// against a `<PortfolioContext.Provider value={...}>` with fixed data
// instead of mocking `fetch` and racing the poll loop.
export { PortfolioContext };
