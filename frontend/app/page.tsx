import { Header } from "@/components/Header";
import { WatchlistPanel } from "@/components/WatchlistPanel";
import { MainChartPanel } from "@/components/MainChartPanel";
import { PlaceholderPanel } from "@/components/PlaceholderPanel";

/** Terminal grid shell (01-UI-SPEC.md "Phase 1 Surface Notes" — layout
 * shell ASCII): header on top; 320px watchlist column; center column with
 * the main chart (~60%) over a 3-up placeholder row (~40%); 340px AI-chat
 * rail. Desktop-first (>=1280px / Tailwind `xl`); the chat rail and 3-up
 * row collapse/stack below that per the tablet behavior notes. */
export default function Home() {
  return (
    <div className="flex h-screen flex-col">
      <Header />
      <div className="flex min-h-0 flex-1 gap-4 p-4">
        <div className="w-[320px] shrink-0 overflow-y-auto">
          <WatchlistPanel />
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-4">
          <div className="min-h-0 flex-[3]">
            <MainChartPanel />
          </div>
          <div className="grid min-h-0 flex-[2] grid-cols-1 gap-4 md:grid-cols-3">
            <PlaceholderPanel
              heading="Portfolio heatmap"
              body="Visualize your holdings by weight and P&L — coming in Phase 3."
            />
            <PlaceholderPanel
              heading="No positions yet"
              body="Buy your first shares to see them here — coming in Phase 2."
            />
            <PlaceholderPanel
              heading="Performance chart"
              body="Track your portfolio value over time — coming in Phase 3."
            />
          </div>
        </div>

        <div className="hidden w-[340px] shrink-0 xl:block">
          <PlaceholderPanel
            className="h-full"
            heading="AI Assistant"
            body="Chat with FinAlly to analyze your portfolio and execute trades — coming in Phase 4."
            footer={
              <input
                type="text"
                disabled
                tabIndex={-1}
                aria-hidden="true"
                placeholder="Message FinAlly…"
                className="pointer-events-none mt-4 w-full rounded-panel border border-border-muted bg-canvas px-3 py-2 text-sm text-neutral placeholder:text-neutral"
              />
            }
          />
        </div>
      </div>
    </div>
  );
}
