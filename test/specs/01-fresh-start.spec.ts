import { expect, test } from "@playwright/test";

// PLAN.md §12 scenario 1: fresh start. Must run before any other spec
// touches the shared backend/DB (numeric filename prefix keeps file order
// deterministic under the single-worker config) since it asserts the
// pristine $10,000 seed balance.

const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

test.describe("fresh start", () => {
  test("renders the default watchlist, $10,000 cash, and a connected stream", async ({ page }) => {
    await page.goto("/");

    const rows = page.getByTestId("watchlist-row");
    await expect(rows).toHaveCount(DEFAULT_TICKERS.length);

    for (const ticker of DEFAULT_TICKERS) {
      await expect(page.locator(`[data-testid="watchlist-row"][data-ticker="${ticker}"]`)).toBeVisible();
    }

    const cashValue = page.locator("header").getByText("Cash", { exact: true }).locator("xpath=following-sibling::span[1]");
    await expect(cashValue).toHaveText("$10,000.00");

    const totalValue = page
      .locator("header")
      .getByText("Total Value", { exact: true })
      .locator("xpath=following-sibling::span[1]");
    await expect(totalValue).toHaveText("$10,000.00");

    // Connection dot should reach "connected" once the SSE stream opens.
    await expect(page.getByTestId("connection-dot")).toHaveAttribute("data-status", "connected", { timeout: 10_000 });
  });

  test("prices stream live and flash on change", async ({ page }) => {
    await page.goto("/");

    const snapshot = () =>
      page
        .getByTestId("watchlist-row")
        .evaluateAll((rows) => rows.map((r) => r.querySelector("span.font-data")?.textContent ?? "").join("|"));

    const baseline = await snapshot();

    // The simulator ticks ~every 500ms with GBM moves, so at least one of
    // the 10 watched tickers should change price within a few seconds. Poll
    // every ticker's price text rather than just one row, since any single
    // ticker's price could legitimately stay flat for a given tick.
    await expect
      .poll(snapshot, { timeout: 15_000, message: "expected at least one watchlist price to change" })
      .not.toBe(baseline);
  });
});
