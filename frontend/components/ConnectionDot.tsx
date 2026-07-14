"use client";

import { usePriceStream } from "@/lib/PriceStreamContext";
import type { ConnectionStatus } from "@/lib/PriceStreamContext";

const STATE_META: Record<ConnectionStatus, { dotClass: string; label: string; textClass: string }> = {
  connected: { dotClass: "bg-positive", label: "Connected", textClass: "text-positive" },
  reconnecting: {
    // 1.5s opacity pulse (0.5<->1.0), per 01-UI-SPEC.md "Connection status dot"
    // (Tailwind's default animate-pulse is 2s — overridden via arbitrary value).
    dotClass: "bg-accent-yellow animate-[pulse_1.5s_ease-in-out_infinite]",
    label: "Reconnecting…",
    textClass: "text-accent-yellow",
  },
  disconnected: { dotClass: "bg-negative", label: "Disconnected", textClass: "text-negative" },
};

/** 8px CSS-drawn connection status dot, driven solely by the real
 * EventSource lifecycle (PriceStreamContext.status) — it cannot show
 * "connected" without an open stream (01-UI-SPEC.md, threat T-03-02). */
export function ConnectionDot() {
  const { status } = usePriceStream();
  const meta = STATE_META[status];

  return (
    <div className="flex items-center gap-2">
      <span className={`h-2 w-2 rounded-full ${meta.dotClass}`} aria-hidden="true" />
      <span className={`text-xs ${meta.textClass}`}>{meta.label}</span>
    </div>
  );
}
