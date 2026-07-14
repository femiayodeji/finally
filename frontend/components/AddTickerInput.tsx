"use client";

import { useState, type KeyboardEvent } from "react";
import { useWatchlist } from "@/lib/WatchlistContext";
import { ApiRequestError } from "@/lib/api";

/** Full-width inline add-ticker input (01-UI-SPEC.md "Watchlist panel" +
 * Copywriting Contract). Uppercases as typed, submits on Enter — no button,
 * no confirmation dialog (D-04/D-03). Server validation errors (400s from
 * `POST /api/watchlist`, surfaced via WatchlistContext.add() -> ApiRequestError)
 * render inline in `negative` red directly beneath the input; never a
 * toast/modal. Duplicate adds are idempotent — the server returns success,
 * so this just clears the field with no error shown. */
export function AddTickerInput() {
  const { add } = useWatchlist();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleKeyDown = async (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    const ticker = value.trim();
    if (!ticker || submitting) return;
    setSubmitting(true);
    try {
      await add(ticker);
      setValue("");
      setError(null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to add ticker");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mb-3 shrink-0">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value.toUpperCase())}
        onKeyDown={handleKeyDown}
        placeholder="Add ticker (e.g. PYPL)"
        aria-label="Add ticker"
        className="h-10 w-full rounded-panel border border-border-muted bg-canvas px-3 text-sm text-white placeholder:text-neutral focus:border-accent-blue focus:outline-none focus:ring-1 focus:ring-accent-blue"
      />
      {error && <p className="mt-2 text-xs text-negative">{error}</p>}
    </div>
  );
}
