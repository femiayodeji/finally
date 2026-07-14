import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Display face — used sparingly for the wordmark and section headers.
const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["500", "700"],
});

// UI/body face — labels, buttons, chat copy.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

// Data face — every number on the terminal (prices, quantities, P&L,
// timestamps) renders in this so columns of figures actually align.
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "FinAlly — AI Trading Workstation",
  description: "Live market data, a simulated portfolio, and an AI copilot that can analyze positions and trade on your behalf.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable} h-full`}
    >
      <body className="h-full bg-base text-ink font-body antialiased">
        {children}
      </body>
    </html>
  );
}
