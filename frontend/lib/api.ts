import type {
  ChatResponse,
  Portfolio,
  PortfolioHistoryResponse,
  PriceHistoryResponse,
  TradeResult,
  TradeSide,
  WatchlistResponse,
} from "./types";

/** All calls are same-origin `/api/*` (PLAN.md §10) — proxied to the
 * backend in dev via next.config.ts, served by FastAPI directly in prod. */
const BASE = "/api";

class ApiRequestError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response had no JSON body; fall back to statusText
    }
    throw new ApiRequestError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export { ApiRequestError };

export function getPortfolio(): Promise<Portfolio> {
  return request<Portfolio>("/portfolio");
}

export function getPortfolioHistory(): Promise<PortfolioHistoryResponse> {
  return request<PortfolioHistoryResponse>("/portfolio/history");
}

export function executeTrade(
  ticker: string,
  side: TradeSide,
  quantity: number,
): Promise<TradeResult> {
  return request<TradeResult>("/portfolio/trade", {
    method: "POST",
    body: JSON.stringify({ ticker, side, quantity }),
  });
}

export function getWatchlist(): Promise<WatchlistResponse> {
  return request<WatchlistResponse>("/watchlist");
}

export function addToWatchlist(ticker: string): Promise<{ ticker: string }> {
  return request<{ ticker: string }>("/watchlist", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export function removeFromWatchlist(ticker: string): Promise<{ ticker: string }> {
  return request<{ ticker: string }>(`/watchlist/${encodeURIComponent(ticker)}`, {
    method: "DELETE",
  });
}

export function getPriceHistory(ticker: string): Promise<PriceHistoryResponse> {
  return request<PriceHistoryResponse>(`/prices/${encodeURIComponent(ticker)}/history`);
}

export function sendChatMessage(message: string): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}
