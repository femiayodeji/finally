"use client";

import { useState, type FormEvent } from "react";
import { useWatchlist } from "@/lib/WatchlistContext";
import { Panel } from "../ui/Panel";
import { WatchlistRow } from "./WatchlistRow";

interface WatchlistPanelProps {
  selectedTicker: string | null;
  onSelectTicker: (ticker: string) => void;
}

export function WatchlistPanel({ selectedTicker, onSelectTicker }: WatchlistPanelProps) {
  const { entries, loading, error, add, remove } = useWatchlist();
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault();
    const ticker = draft.trim();
    if (!ticker) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await add(ticker);
      setDraft("");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add ticker");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Panel
      title="Watchlist"
      className="h-full"
      bodyClassName="overflow-y-auto"
      action={
        <form onSubmit={handleAdd} className="flex items-center gap-1">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value.toUpperCase())}
            placeholder="TICKER"
            maxLength={5}
            aria-label="Add ticker to watchlist"
            className="w-16 border border-line bg-base px-1.5 py-0.5 font-data text-[11px] text-ink placeholder:text-ink-faint focus:border-blue focus:outline-none"
          />
          <button
            type="submit"
            disabled={submitting || !draft.trim()}
            className="border border-blue/40 bg-blue/20 px-1.5 py-0.5 font-display text-[11px] text-blue transition-colors hover:bg-blue/30 disabled:opacity-40"
          >
            Add
          </button>
        </form>
      }
    >
      {formError && <p className="px-3 py-1 font-body text-xs text-down">{formError}</p>}
      {error && <p className="px-3 py-1 font-body text-xs text-down">{error}</p>}
      {loading && entries.length === 0 && (
        <p className="px-3 py-2 font-body text-xs text-ink-faint">Loading…</p>
      )}
      {!loading && entries.length === 0 && !error && (
        <p className="px-3 py-2 font-body text-xs text-ink-faint">
          No tickers yet — add one above.
        </p>
      )}
      {entries.map((entry) => (
        <WatchlistRow
          key={entry.ticker}
          initial={entry}
          selected={entry.ticker === selectedTicker}
          onSelect={onSelectTicker}
          onRemove={remove}
        />
      ))}
    </Panel>
  );
}
