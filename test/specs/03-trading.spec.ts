import { expect, test } from "@playwright/test";

// PLAN.md §12 scenarios 3 & 4: buy and sell shares. Two tickers are used so
// the "position updates" (partial sell) and "position disappears" (sell to
// zero) paths can both be exercised without one interfering with the other.
const PARTIAL_TICKER = "AAPL"; // bought then partially sold — stays open for 04-portfolio-viz
const CLOSE_TICKER = "GOOGL"; // bought then fully sold — row should disappear

function parseCurrency(text: string): number {
  return Number(text.replace(/[^0-9.-]/g, ""));
}

async function readCash(page: import("@playwright/test").Page): Promise<number> {
  const cashValue = page.locator("header").getByText("Cash", { exact: true }).locator("xpath=following-sibling::span[1]");
  return parseCurrency((await cashValue.textContent()) ?? "0");
}

async function trade(
  page: import("@playwright/test").Page,
  ticker: string,
  quantity: number,
  side: "Buy" | "Sell",
) {
  await page.getByLabel("Ticker").fill(ticker);
  await page.getByLabel("Quantity").fill(String(quantity));
  await page.getByRole("button", { name: side, exact: true }).click();
}

test.describe("trading", () => {
  test("buying decreases cash and opens a position", async ({ page }) => {
    await page.goto("/");
    const cashBefore = await readCash(page);

    await trade(page, PARTIAL_TICKER, 4, "Buy");

    await expect(page.getByText(/^Bought 4 AAPL @/)).toBeVisible({ timeout: 10_000 });
    await expect
      .poll(async () => readCash(page), { timeout: 10_000, message: "expected cash to decrease after buying" })
      .toBeLessThan(cashBefore);

    const positionRow = page.locator('[data-testid="position-row"]', { hasText: PARTIAL_TICKER });
    await expect(positionRow).toBeVisible();
  });

  test("selling part of a position increases cash and keeps the position open", async ({ page }) => {
    await page.goto("/");
    const positionRow = page.locator('[data-testid="position-row"]', { hasText: PARTIAL_TICKER });
    await expect(positionRow).toBeVisible();
    const qtyBefore = Number((await positionRow.locator("td").nth(1).textContent())?.trim());
    const cashBefore = await readCash(page);

    await trade(page, PARTIAL_TICKER, 1, "Sell");

    await expect(page.getByText(/^Sold 1 AAPL @/)).toBeVisible({ timeout: 10_000 });
    await expect
      .poll(async () => readCash(page), { timeout: 10_000, message: "expected cash to increase after selling" })
      .toBeGreaterThan(cashBefore);

    await expect(positionRow).toBeVisible();
    const qtyAfter = Number((await positionRow.locator("td").nth(1).textContent())?.trim());
    expect(qtyAfter).toBeLessThan(qtyBefore);
    expect(qtyAfter).toBeGreaterThan(0);
  });

  test("buying then fully selling closes the position (row disappears)", async ({ page }) => {
    await page.goto("/");

    await trade(page, CLOSE_TICKER, 2, "Buy");
    const positionRow = page.locator('[data-testid="position-row"]', { hasText: CLOSE_TICKER });
    await expect(positionRow).toBeVisible({ timeout: 10_000 });

    await trade(page, CLOSE_TICKER, 2, "Sell");
    await expect(page.getByText(/^Sold 2 GOOGL @/)).toBeVisible({ timeout: 10_000 });
    await expect(positionRow).toHaveCount(0, { timeout: 10_000 });
  });
});
