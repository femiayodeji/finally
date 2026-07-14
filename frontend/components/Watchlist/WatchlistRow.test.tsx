import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { WatchlistEntry } from "@/lib/types";
import { WatchlistRow } from "./WatchlistRow";

const baseEntry: WatchlistEntry = {
  ticker: "AAPL",
  price: 190,
  previous_price: 189,
  change: 1,
  session_change_percent: 0.5,
  direction: "up",
  timestamp: 1000,
};

describe("WatchlistRow", () => {
  it("renders the ticker, price, and server-computed change % from the snapshot", () => {
    render(<WatchlistRow initial={baseEntry} selected={false} onSelect={() => {}} onRemove={() => {}} />);
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("$190.00")).toBeInTheDocument();
    expect(screen.getByText("+0.50%")).toBeInTheDocument();
  });

  it("has no flash overlay on first render", () => {
    render(<WatchlistRow initial={baseEntry} selected={false} onSelect={() => {}} onRemove={() => {}} />);
    expect(screen.queryByTestId("price-flash")).not.toBeInTheDocument();
  });

  it("flashes green on an uptick when the price changes", () => {
    const { rerender } = render(
      <WatchlistRow initial={baseEntry} selected={false} onSelect={() => {}} onRemove={() => {}} />,
    );

    rerender(
      <WatchlistRow
        initial={{ ...baseEntry, price: 192, session_change_percent: 1.5 }}
        selected={false}
        onSelect={() => {}}
        onRemove={() => {}}
      />,
    );

    const flash = screen.getByTestId("price-flash");
    expect(flash).toHaveClass("flash-up");
  });

  it("flashes red on a downtick when the price changes", () => {
    const { rerender } = render(
      <WatchlistRow initial={baseEntry} selected={false} onSelect={() => {}} onRemove={() => {}} />,
    );

    rerender(
      <WatchlistRow
        initial={{ ...baseEntry, price: 185, session_change_percent: -2.6, direction: "down" }}
        selected={false}
        onSelect={() => {}}
        onRemove={() => {}}
      />,
    );

    const flash = screen.getByTestId("price-flash");
    expect(flash).toHaveClass("flash-down");
  });
});
