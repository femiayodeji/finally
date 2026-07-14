"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { PriceStreamFrame, PriceUpdate } from "./types";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

interface PriceStreamValue {
  prices: PriceStreamFrame;
  status: ConnectionStatus;
}

const PriceStreamContext = createContext<PriceStreamValue>({
  prices: {},
  status: "disconnected",
});

// If a reconnect attempt hasn't succeeded within this window, the header dot
// drops from yellow to red. `EventSource` keeps retrying underneath
// regardless — this only governs what the UI reports.
const DISCONNECTED_AFTER_MS = 8000;

/** Single shared `EventSource('/api/stream/prices')` connection (PLAN.md
 * §6/§10) — the source of truth for live prices. Mounted once near the root
 * so every consumer (watchlist, header, chart) reads from the same frame
 * instead of opening its own connection. */
export function PriceStreamProvider({ children }: { children: React.ReactNode }) {
  const [prices, setPrices] = useState<PriceStreamFrame>({});
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const disconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (typeof EventSource === "undefined") return;

    const source = new EventSource("/api/stream/prices");

    const clearDisconnectTimer = () => {
      if (disconnectTimer.current) {
        clearTimeout(disconnectTimer.current);
        disconnectTimer.current = null;
      }
    };

    source.onopen = () => {
      clearDisconnectTimer();
      setStatus("connected");
    };

    source.onmessage = (event) => {
      clearDisconnectTimer();
      setStatus("connected");
      try {
        const frame = JSON.parse(event.data) as PriceStreamFrame;
        setPrices((prev) => ({ ...prev, ...frame }));
      } catch {
        // malformed frame — skip, keep the last good prices on screen
      }
    };

    source.onerror = () => {
      setStatus("reconnecting");
      if (!disconnectTimer.current) {
        disconnectTimer.current = setTimeout(() => {
          setStatus("disconnected");
        }, DISCONNECTED_AFTER_MS);
      }
    };

    return () => {
      clearDisconnectTimer();
      source.close();
    };
  }, []);

  return (
    <PriceStreamContext.Provider value={{ prices, status }}>
      {children}
    </PriceStreamContext.Provider>
  );
}

export function usePriceStream(): PriceStreamValue {
  return useContext(PriceStreamContext);
}

export function useTickerPrice(ticker: string): PriceUpdate | undefined {
  const { prices } = usePriceStream();
  return prices[ticker];
}
