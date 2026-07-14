import { Panel } from "./Panel";

/** Thin placeholder — Plan 05 replaces this body with the live add-ticker
 * input, sparkline rows, and price-flash mechanics (01-UI-SPEC.md
 * "Watchlist panel"). Kept as a standalone file now so that plan can ship
 * without touching layout.tsx/page.tsx. */
export function WatchlistPanel() {
  return (
    <Panel className="h-full w-full items-center justify-center text-center">
      <p className="text-xs text-neutral">streaming…</p>
    </Panel>
  );
}
