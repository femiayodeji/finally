import { expect, test } from "@playwright/test";

// PLAN.md §12 scenario 7: SSE resilience — disconnect and verify reconnection.
// `EventSource` is browser-native and retries automatically (the stream
// sends `retry: 1000` — see backend/app/market/stream.py); simulating a
// network drop via the browser context is the most realistic way to exercise
// that without reaching into React internals.

test.describe("SSE resilience", () => {
  test("prices resume streaming after a connection drop", async ({ page, context }) => {
    await page.goto("/");
    await expect(page.getByTestId("connection-dot")).toHaveAttribute("data-status", "connected", { timeout: 10_000 });

    await context.setOffline(true);
    await expect(page.getByTestId("connection-dot")).toHaveAttribute("data-status", "reconnecting", {
      timeout: 15_000,
    });

    await context.setOffline(false);
    await expect(page.getByTestId("connection-dot")).toHaveAttribute("data-status", "connected", { timeout: 15_000 });

    // And prices should actually resume ticking, not just the status dot.
    const snapshot = () =>
      page
        .getByTestId("watchlist-row")
        .evaluateAll((rows) => rows.map((r) => r.querySelector("span.font-data")?.textContent ?? "").join("|"));
    const baseline = await snapshot();
    await expect
      .poll(snapshot, { timeout: 15_000, message: "expected prices to resume updating after reconnect" })
      .not.toBe(baseline);
  });
});
