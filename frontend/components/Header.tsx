import { ConnectionDot } from "./ConnectionDot";

/** 56px header bar (01-UI-SPEC.md "Header"). Total value / cash are stubs
 * until Plan 02 wires /api/portfolio — a literal em-dash in `neutral`, never
 * "$0.00" (which would misleadingly imply a computed-but-zero balance). */
export function Header() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border-muted bg-panel px-4">
      <span className="text-lg font-semibold text-accent-yellow">FinAlly</span>
      <div className="flex items-center gap-8">
        <ConnectionDot />
        <StubFigure label="TOTAL VALUE" />
        <StubFigure label="CASH" />
      </div>
    </header>
  );
}

function StubFigure({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-end">
      <span className="text-xs text-neutral">{label}</span>
      <span className="numeric text-[28px] font-semibold leading-tight text-neutral">—</span>
    </div>
  );
}
