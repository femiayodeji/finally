"use client";

import { createContext, useContext, useState } from "react";

interface SelectedTickerContextValue {
  selected: string | null;
  setSelected: (ticker: string | null) => void;
}

const SelectedTickerContext = createContext<SelectedTickerContextValue>({
  selected: null,
  setSelected: () => {},
});

/** Shared "which ticker is the main chart showing" state. This is the seam
 * that lets the watchlist (Plan 05, sets selection on row click) and the
 * main chart (Plan 06, reads selection to fetch/render) ship as parallel
 * plans without either editing the other's files. */
export function SelectedTickerProvider({ children }: { children: React.ReactNode }) {
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <SelectedTickerContext.Provider value={{ selected, setSelected }}>
      {children}
    </SelectedTickerContext.Provider>
  );
}

export function useSelectedTicker(): SelectedTickerContextValue {
  return useContext(SelectedTickerContext);
}
