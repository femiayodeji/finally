"use client";

import { useWatchlist } from "@/lib/WatchlistContext";
import { Panel } from "./Panel";
import { AddTickerInput } from "./AddTickerInput";
import { WatchlistRow } from "./WatchlistRow";

/** Live, editable watchlist (01-UI-SPEC.md "Watchlist panel") — replaces the
 * Plan 03 placeholder. Add-ticker input on top, one WatchlistRow per tracked
 * ticker in persisted order below. Rows get all live pricing from the SSE
 * context via WatchlistRow itself; this panel only calls the watchlist API
 * for CRUD (add/remove) — no REST polling for price refreshes (UI-10). The
 * row list bleeds to the panel's edges (`-mx-4`, cancelling Panel's 16px
 * padding) so the selected-row tint and hover-remove hit area can reach the
 * panel border, while each row keeps its own 12px horizontal padding. */
export function WatchlistPanel() {
  const { entries, loading } = useWatchlist();
  const isEmpty = !loading && entries.length === 0;

  return (
    <Panel className="h-full w-full">
      <AddTickerInput />
      {isEmpty ? (
        <div className="flex flex-1 flex-col items-center justify-center px-4 py-8 text-center">
          <p className="text-lg font-semibold text-neutral">Your watchlist is empty</p>
          <p className="mt-2 text-xs text-neutral">
            Type a ticker symbol above and press Enter to start streaming.
          </p>
        </div>
      ) : (
        <div className="-mx-4 flex flex-col">
          {entries.map((entry) => (
            <WatchlistRow key={entry.ticker} entry={entry} />
          ))}
        </div>
      )}
    </Panel>
  );
}
