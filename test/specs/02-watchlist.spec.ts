import { expect, test } from "@playwright/test";

// PLAN.md §12 scenario 2: add and remove a watchlist ticker. Uses a symbol
// well outside the default seed list so it can't collide with 01's assertions.
const TICKER = "PYPL";

test.describe("watchlist add/remove", () => {
  test("adds a ticker via the panel form and removes it again", async ({ page }) => {
    await page.goto("/");

    const row = page.locator(`[data-testid="watchlist-row"][data-ticker="${TICKER}"]`);
    await expect(row).toHaveCount(0);

    await page.getByLabel("Add ticker to watchlist").fill(TICKER);
    await page.getByRole("button", { name: "Add", exact: true }).click();

    await expect(row).toBeVisible({ timeout: 10_000 });
    // Simulator mode assigns a deterministic seed price to any well-formed
    // symbol (PLAN.md §6/§8) — it shouldn't sit at the "—" placeholder for long.
    await expect(row.locator("span.font-data").first()).not.toHaveText("—", { timeout: 10_000 });

    await page.getByLabel(`Remove ${TICKER} from watchlist`).click();
    await expect(row).toHaveCount(0);
  });
});
