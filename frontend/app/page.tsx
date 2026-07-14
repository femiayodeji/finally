"use client";

import { useState } from "react";
import { Header } from "@/components/Header";
import { WatchlistPanel } from "@/components/Watchlist/WatchlistPanel";
import { MainChart } from "@/components/Chart/MainChart";
import { Heatmap } from "@/components/Portfolio/Heatmap";
import { PnLChart } from "@/components/Portfolio/PnLChart";
import { PositionsTable } from "@/components/Portfolio/PositionsTable";
import { TradeBar } from "@/components/Trade/TradeBar";
import { ChatPanel } from "@/components/Chat/ChatPanel";
import { PriceStreamProvider } from "@/lib/PriceStreamContext";
import { PortfolioProvider } from "@/lib/PortfolioContext";
import { WatchlistProvider } from "@/lib/WatchlistContext";

export default function Home() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(true);

  return (
    <PriceStreamProvider>
      <PortfolioProvider>
        <WatchlistProvider>
          <div className="flex h-screen flex-col overflow-hidden bg-base">
            <Header chatOpen={chatOpen} onToggleChat={() => setChatOpen((v) => !v)} />

            <div className="flex min-h-0 flex-1">
              <div className="w-64 shrink-0 border-r border-line">
                <WatchlistPanel selectedTicker={selectedTicker} onSelectTicker={setSelectedTicker} />
              </div>

              <main className="min-w-0 flex-1 overflow-y-auto p-3">
                <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
                  <div className="h-[380px] lg:col-span-2">
                    <MainChart ticker={selectedTicker} />
                  </div>
                  <div className="h-[380px] lg:col-span-1">
                    <Heatmap />
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-3">
                  <div className="h-[300px] lg:col-span-2">
                    <PositionsTable />
                  </div>
                  <div className="h-[300px] lg:col-span-1">
                    <PnLChart />
                  </div>
                </div>

                <div className="mt-3">
                  <TradeBar selectedTicker={selectedTicker} />
                </div>
              </main>

              <ChatPanel open={chatOpen} />
            </div>
          </div>
        </WatchlistProvider>
      </PortfolioProvider>
    </PriceStreamProvider>
  );
}
