import type { ConnectionStatus } from "@/lib/PriceStreamContext";

const STATUS: Record<ConnectionStatus, { dot: string; label: string; pulse: boolean }> = {
  connected: { dot: "bg-up", label: "Connected", pulse: false },
  reconnecting: { dot: "bg-yellow", label: "Reconnecting", pulse: true },
  disconnected: { dot: "bg-down", label: "Disconnected", pulse: true },
};

/** Header status dot — green/yellow/red per PLAN.md §2. */
export function ConnectionDot({ status }: { status: ConnectionStatus }) {
  const s = STATUS[status];
  return (
    <span className="flex items-center gap-1.5" title={s.label} data-testid="connection-dot" data-status={status}>
      <span className={`h-2 w-2 rounded-full ${s.dot} ${s.pulse ? "pulse-dot" : ""}`} />
      <span className="hidden font-body text-[11px] text-ink-dim sm:inline">{s.label}</span>
    </span>
  );
}
