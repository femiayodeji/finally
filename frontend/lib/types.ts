// Types mirror planning/BUILD_PLAN.md §8 exactly. The frontend never derives
// these fields itself (change %, P&L, valuation, history) — it only ever
// displays what the backend sends.

export type TradeSide = "buy" | "sell";
export type Direction = "up" | "down" | "flat";
export type WatchlistAction = "add" | "remove";

/** One ticker's entry in the `GET /api/stream/prices` SSE payload. */
export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  session_change_percent: number;
  direction: Direction;
}

/** Keyed-by-ticker SSE frame: `{"AAPL": {...}, "GOOGL": {...}}`. */
export type PriceStreamFrame = Record<string, PriceUpdate>;

export interface PricePoint {
  timestamp: number;
  price: number;
}

export interface PriceHistoryResponse {
  ticker: string;
  history: PricePoint[];
}

export interface WatchlistEntry {
  ticker: string;
  price: number | null;
  previous_price: number | null;
  change: number | null;
  session_change_percent: number | null;
  direction: Direction | null;
  timestamp: number | null;
}

export interface WatchlistResponse {
  watchlist: WatchlistEntry[];
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
}

export interface Portfolio {
  cash_balance: number;
  positions_value: number;
  total_value: number;
  total_unrealized_pnl: number;
  positions: Position[];
}

export interface Trade {
  id: string;
  ticker: string;
  side: TradeSide;
  quantity: number;
  price: number;
  executed_at: string;
}

export interface TradeResult {
  trade: Trade;
  portfolio: Portfolio;
}

export interface PortfolioSnapshot {
  total_value: number;
  recorded_at: string;
}

export interface PortfolioHistoryResponse {
  history: PortfolioSnapshot[];
}

export interface ChatTradeAction {
  ticker: string;
  side: TradeSide;
  quantity: number;
  executed: boolean;
  error?: string;
}

export interface ChatWatchlistAction {
  ticker: string;
  action: WatchlistAction;
  executed: boolean;
  error?: string;
}

export interface ChatResponse {
  message: string;
  actions: {
    trades: ChatTradeAction[];
    watchlist_changes: ChatWatchlistAction[];
  };
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions?: ChatResponse["actions"] | null;
  created_at: string;
}

export interface ApiError {
  detail: string;
}
