import type { ChatMessage as ChatMessageType } from "@/lib/types";
import { formatQuantity } from "@/lib/format";

export function ChatMessageBubble({ message }: { message: ChatMessageType }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] border px-3 py-2 font-body text-sm ${
          isUser ? "border-blue/40 bg-blue/10 text-ink" : "border-line bg-panel-alt text-ink"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.actions && <ActionSummary actions={message.actions} />}
      </div>
    </div>
  );
}

/** Trade executions and watchlist changes the AI made, shown inline as
 * confirmations (PLAN.md §10) — success/failure per action, since the
 * backend validates and may reject an individual trade even when the chat
 * turn overall succeeds. */
function ActionSummary({ actions }: { actions: NonNullable<ChatMessageType["actions"]> }) {
  const items = [
    ...actions.trades.map((t) => ({
      key: `trade-${t.ticker}-${t.side}`,
      ok: t.executed,
      text: t.executed
        ? `${t.side === "buy" ? "Bought" : "Sold"} ${formatQuantity(t.quantity)} ${t.ticker}`
        : `Failed to ${t.side} ${t.ticker}`,
      error: t.error,
    })),
    ...actions.watchlist_changes.map((w) => ({
      key: `watchlist-${w.ticker}-${w.action}`,
      ok: w.executed,
      text: w.executed
        ? `${w.action === "add" ? "Added" : "Removed"} ${w.ticker} ${w.action === "add" ? "to" : "from"} watchlist`
        : `Failed to ${w.action} ${w.ticker}`,
      error: w.error,
    })),
  ];
  if (items.length === 0) return null;

  return (
    <ul className="mt-2 space-y-1 border-t border-line-soft pt-2">
      {items.map((item) => (
        <li key={item.key} className={`font-data text-xs ${item.ok ? "text-up" : "text-down"}`}>
          {item.ok ? "✓" : "✕"} {item.text}
          {item.error && <span className="ml-1 text-ink-faint">({item.error})</span>}
        </li>
      ))}
    </ul>
  );
}
