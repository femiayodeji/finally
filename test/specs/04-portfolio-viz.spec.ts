import { expect, test } from "@playwright/test";

// PLAN.md §12 scenario 5: heatmap renders with colored cells, P&L chart has
// data points. Ensures an open position exists via a direct API call (rather
// than relying on 03-trading's side effects) so this spec is self-contained.
const TICKER = "MSFT";

test.describe("portfolio visualization", () => {
  test.beforeAll(async ({ request }) => {
    const res = await request.post("/api/portfolio/trade", {
      data: { ticker: TICKER, quantity: 1, side: "buy" },
    });
    expect(res.ok()).toBeTruthy();
  });

  test("heatmap renders colored treemap cells for open positions", async ({ page }) => {
    await page.goto("/");

    const heatmapPanel = page.locator("section", { has: page.getByRole("heading", { name: "Positions Heatmap" }) });
    const cells = heatmapPanel.locator("svg rect");
    await expect(cells.first()).toBeVisible({ timeout: 10_000 });
    const fillCount = await cells.evaluateAll(
      (rects) => rects.filter((r) => (r.getAttribute("fill") ?? "").startsWith("rgba(")).length,
    );
    expect(fillCount).toBeGreaterThan(0);
  });

  test("P&L chart has recorded snapshot data points", async ({ page, request }) => {
    // Trade execution snapshots the portfolio immediately (PLAN.md §7/§8), so
    // by this point at least one portfolio_snapshots row must exist.
    const historyRes = await request.get("/api/portfolio/history");
    const history = (await historyRes.json()).history as unknown[];
    expect(history.length).toBeGreaterThan(0);

    await page.goto("/");
    const pnlPanel = page.locator("section", { has: page.getByRole("heading", { name: "Portfolio Value" }) });
    // lightweight-charts renders onto a <canvas>; its presence confirms the
    // chart mounted (the data itself is verified against the API above,
    // since canvas pixel content isn't practical to assert against).
    await expect(pnlPanel.locator("canvas").first()).toBeVisible({ timeout: 10_000 });
  });
});
