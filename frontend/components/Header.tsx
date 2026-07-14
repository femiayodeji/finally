"use client";

import { usePortfolio } from "@/lib/PortfolioContext";
import { usePriceStream } from "@/lib/PriceStreamContext";
import { formatCurrency } from "@/lib/format";
import { ConnectionDot } from "./ui/ConnectionDot";

export function Header({ chatOpen, onToggleChat }: { chatOpen: boolean; onToggleChat: () => void }) {
  const { portfolio } = usePortfolio();
  const { status } = usePriceStream();
  const pnl = portfolio?.total_unrealized_pnl;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-panel px-4">
      <div className="flex items-baseline gap-2">
        <span className="font-display text-lg font-bold tracking-tight text-ink">
          FinAlly
        </span>
        <span className="hidden font-body text-[11px] text-ink-faint sm:inline">
          AI Trading Workstation
        </span>
      </div>

      <div className="flex items-center gap-6">
        <Stat
          label="Total Value"
          value={portfolio ? formatCurrency(portfolio.total_value) : "—"}
          valueClassName="text-ink"
        />
        <Stat
          label="Cash"
          value={portfolio ? formatCurrency(portfolio.cash_balance) : "—"}
          valueClassName="text-ink-dim"
        />
        <Stat
          label="Unrealized P&L"
          value={pnl != null ? formatCurrency(pnl) : "—"}
          valueClassName={pnl == null ? "text-ink-dim" : pnl >= 0 ? "text-up" : "text-down"}
        />

        <div className="hidden h-8 w-px bg-line md:block" />

        <ConnectionDot status={status} />

        <button
          type="button"
          onClick={onToggleChat}
          className="border border-purple/50 bg-purple/20 px-3 py-1.5 font-display text-[11px] font-medium uppercase tracking-wide text-purple transition-colors hover:bg-purple/30"
          aria-pressed={chatOpen}
        >
          {chatOpen ? "Hide AI" : "AI Chat"}
        </button>
      </div>
    </header>
  );
}

function Stat({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: string;
  valueClassName: string;
}) {
  return (
    <div className="flex flex-col items-end leading-tight">
      <span className="font-body text-[10px] uppercase tracking-wide text-ink-faint">{label}</span>
      <span className={`font-data text-sm font-medium ${valueClassName}`}>{value}</span>
    </div>
  );
}
