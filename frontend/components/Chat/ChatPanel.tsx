"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiRequestError, sendChatMessage } from "@/lib/api";
import { usePortfolio } from "@/lib/PortfolioContext";
import { useWatchlist } from "@/lib/WatchlistContext";
import type { ChatMessage } from "@/lib/types";
import { ChatMessageBubble } from "./ChatMessage";

let localIdSeq = 0;
const nextLocalId = () => `local-${Date.now()}-${localIdSeq++}`;

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "I'm FinAlly, your AI trading assistant. Ask about your portfolio, get an opinion on a position, or tell me what to trade.",
  created_at: new Date(0).toISOString(),
};

/** Docked, collapsible AI chat sidebar (PLAN.md §10). No `GET /api/chat`
 * history endpoint exists in the API contract (§8) — this panel's history
 * is session-local; the backend still persists every turn for its own
 * conversation context (PLAN.md §9). */
export function ChatPanel({ open }: { open: boolean }) {
  const { refresh: refreshPortfolio } = usePortfolio();
  const { refresh: refreshWatchlist } = useWatchlist();
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Optional chaining on scrollTo itself, not just the ref: jsdom (used by
    // the component tests) doesn't implement scroll methods on elements.
    scrollRef.current?.scrollTo?.({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const handleSend = async (e: FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { id: nextLocalId(), role: "user", content: text, created_at: new Date().toISOString() }]);
    setDraft("");
    setSending(true);
    setError(null);

    try {
      const res = await sendChatMessage(text);
      setMessages((prev) => [
        ...prev,
        { id: nextLocalId(), role: "assistant", content: res.message, actions: res.actions, created_at: new Date().toISOString() },
      ]);
      // The LLM can execute trades/watchlist changes through its own code
      // path (PLAN.md §9) — resync the panels that own that state.
      if (res.actions.trades.length > 0) await refreshPortfolio();
      if (res.actions.watchlist_changes.length > 0) await refreshWatchlist();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not reach the AI assistant.");
    } finally {
      setSending(false);
    }
  };

  if (!open) return null;

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-l border-line bg-panel">
      <header className="flex shrink-0 items-center gap-2 border-b border-line-soft px-3 py-2">
        <span className="h-2 w-2 rounded-full bg-yellow" />
        <h2 className="font-display text-[11px] font-medium uppercase tracking-[0.14em] text-ink-dim">AI Chat</h2>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto px-3 py-3">
        {messages.map((m) => (
          <ChatMessageBubble key={m.id} message={m} />
        ))}
        {sending && (
          <div className="flex justify-start">
            <div data-testid="chat-loading" className="border border-line bg-panel-alt px-3 py-2 font-data text-xs text-ink-faint">
              thinking…
            </div>
          </div>
        )}
      </div>

      {error && <p className="px-3 pb-1 font-body text-xs text-down">{error}</p>}

      <form onSubmit={handleSend} className="flex shrink-0 gap-2 border-t border-line-soft p-3">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask FinAlly…"
          className="flex-1 border border-line bg-base px-2 py-1.5 font-body text-sm text-ink placeholder:text-ink-faint focus:border-purple focus:outline-none"
        />
        <button
          type="submit"
          disabled={sending || !draft.trim()}
          className="border border-purple bg-purple px-3 py-1.5 font-display text-xs font-semibold uppercase tracking-wide text-ink transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </aside>
  );
}
