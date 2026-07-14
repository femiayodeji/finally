import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PortfolioContext } from "@/lib/PortfolioContext";
import type { Portfolio } from "@/lib/types";
import { PositionsTable } from "./PositionsTable";

const portfolio: Portfolio = {
  cash_balance: 5000,
  positions_value: 1925,
  total_value: 6925,
  total_unrealized_pnl: 25,
  positions: [
    {
      ticker: "AAPL",
      quantity: 10,
      avg_cost: 190,
      current_price: 192.5,
      market_value: 1925,
      unrealized_pnl: 25,
      unrealized_pnl_percent: 1.32,
    },
  ],
};

function renderWithPortfolio(overrides: Partial<React.ContextType<typeof PortfolioContext>> = {}) {
  return render(
    <PortfolioContext.Provider value={{ portfolio, loading: false, error: null, refresh: async () => {}, ...overrides }}>
      <PositionsTable />
    </PortfolioContext.Provider>,
  );
}

describe("PositionsTable", () => {
  it("renders one row per position using the backend-computed figures verbatim", () => {
    renderWithPortfolio();
    const row = screen.getByTestId("position-row");
    expect(row).toHaveTextContent("AAPL");
    expect(row).toHaveTextContent("10");
    expect(row).toHaveTextContent("$190.00");
    expect(row).toHaveTextContent("$192.50");
    expect(row).toHaveTextContent("$25.00");
    expect(row).toHaveTextContent("+1.32%");
  });

  it("shows an empty state with no open positions", () => {
    renderWithPortfolio({ portfolio: { ...portfolio, positions: [] } });
    expect(screen.getByText("No open positions")).toBeInTheDocument();
    expect(screen.queryByTestId("position-row")).not.toBeInTheDocument();
  });

  it("shows a loading state before the first portfolio fetch resolves", () => {
    renderWithPortfolio({ portfolio: null, loading: true });
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });
});
