import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { PriceStreamProvider } from "@/lib/PriceStreamContext";
import { WatchlistProvider } from "@/lib/WatchlistContext";
import { SelectedTickerProvider } from "@/lib/SelectedTickerContext";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "FinAlly",
  description: "FinAlly — AI Trading Workstation",
};

/** Root layout: dark theme, Inter font, and the three providers every panel
 * in the terminal shares — PriceStreamProvider (live SSE prices),
 * WatchlistProvider (tracked tickers), SelectedTickerProvider (which ticker
 * the main chart shows). Mounted once here so no panel opens its own
 * connection or duplicates state (01-UI-SPEC.md, PLAN.md §10). */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <PriceStreamProvider>
          <WatchlistProvider>
            <SelectedTickerProvider>{children}</SelectedTickerProvider>
          </WatchlistProvider>
        </PriceStreamProvider>
      </body>
    </html>
  );
}
