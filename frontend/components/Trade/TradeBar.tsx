"use client";

import { useState } from "react";
import { ApiRequestError, executeTrade } from "@/lib/api";
import { usePortfolio } from "@/lib/PortfolioContext";
import { formatCurrency, formatQuantity } from "@/lib/format";
import type { TradeSide } from "@/lib/types";
import { Panel } from "../ui/Panel";

interface TradeBarProps {
  /** The currently selected watchlist ticker — prefills the field but the
   * user is free to type over it (a click elsewhere resets it). */
  selectedTicker: string | null;
}

export function TradeBar({ selectedTicker }: TradeBarProps) {
  const { refresh } = usePortfolio();
  const [ticker, setTicker] = useState(selectedTicker ?? "");
  const [quantity, setQuantity] = useState("");
  const [submitting, setSubmitting] = useState<TradeSide | null>(null);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  // Adjust `ticker` when the watchlist selection changes, without an effect
  // (React's "adjust state when a prop changes" pattern — see
  // https://react.dev/learn/you-might-not-need-an-effect). Tracking the
  // previous prop value in state lets this run during render instead of as
  // a post-commit effect, so there's no extra render pass.
  const [prevSelectedTicker, setPrevSelectedTicker] = useState(selectedTicker);
  if (selectedTicker !== prevSelectedTicker) {
    setPrevSelectedTicker(selectedTicker);
    if (selectedTicker) setTicker(selectedTicker);
  }

  const handleTrade = async (side: TradeSide) => {
    const qty = Number(quantity);
    if (!ticker.trim() || !Number.isFinite(qty) || qty <= 0) {
      setMessage({ kind: "error", text: "Enter a ticker and a positive quantity." });
      return;
    }
    setSubmitting(side);
    setMessage(null);
    try {
      const result = await executeTrade(ticker.trim().toUpperCase(), side, qty);
      setMessage({
        kind: "success",
        text: `${side === "buy" ? "Bought" : "Sold"} ${formatQuantity(qty)} ${result.trade.ticker} @ ${formatCurrency(result.trade.price)}`,
      });
      setQuantity("");
      await refresh();
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof ApiRequestError ? err.message : "Trade failed" });
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <Panel title="Trade" bodyClassName="flex items-end gap-3 p-3 flex-wrap">
      <Field label="Ticker">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          maxLength={5}
          className="w-20 border border-line bg-base px-2 py-1.5 font-data text-sm text-ink focus:border-blue focus:outline-none"
        />
      </Field>
      <Field label="Quantity">
        <input
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          inputMode="decimal"
          placeholder="0"
          className="w-24 border border-line bg-base px-2 py-1.5 font-data text-sm text-ink focus:border-blue focus:outline-none"
        />
      </Field>
      <button
        type="button"
        onClick={() => handleTrade("buy")}
        disabled={submitting !== null}
        className="border border-blue bg-blue px-4 py-1.5 font-display text-xs font-semibold uppercase tracking-wide text-base transition-opacity hover:opacity-90 disabled:opacity-40"
      >
        {submitting === "buy" ? "Buying…" : "Buy"}
      </button>
      <button
        type="button"
        onClick={() => handleTrade("sell")}
        disabled={submitting !== null}
        className="border border-purple bg-purple px-4 py-1.5 font-display text-xs font-semibold uppercase tracking-wide text-ink transition-opacity hover:opacity-90 disabled:opacity-40"
      >
        {submitting === "sell" ? "Selling…" : "Sell"}
      </button>
      {message && (
        <span className={`font-body text-xs ${message.kind === "success" ? "text-up" : "text-down"}`}>
          {message.text}
        </span>
      )}
    </Panel>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="font-body text-[10px] uppercase tracking-wide text-ink-faint">{label}</span>
      {children}
    </label>
  );
}
