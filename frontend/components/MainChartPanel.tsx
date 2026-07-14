import { Panel } from "./Panel";

/** Thin placeholder — Plan 06 replaces this body with the Lightweight
 * Charts filled-area series driven by useSelectedTicker() + SSE
 * (01-UI-SPEC.md "Main chart panel"). Kept as a standalone file now so that
 * plan can ship without touching layout.tsx/page.tsx. */
export function MainChartPanel() {
  return (
    <Panel className="h-full w-full items-center justify-center text-center">
      <p className="text-xs text-neutral">No chart to show</p>
    </Panel>
  );
}
