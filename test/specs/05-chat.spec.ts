import { expect, test } from "@playwright/test";

// PLAN.md §12 scenario 6: AI chat (mocked). LLM_MOCK=true deterministically
// regex-matches "buy|sell N TICKER" and executes it through the same
// auto-execution path as a manual trade (see llm-engineer's Cross-team note
// in planning/BUILD_PLAN.md).
const TICKER = "NFLX";

test.describe("AI chat", () => {
  test("a mocked trade instruction gets a response and executes inline", async ({ page, request }) => {
    const before = await (await request.get("/api/portfolio")).json();
    const qtyBefore = (before.positions.find((p: { ticker: string }) => p.ticker === TICKER)?.quantity as number) ?? 0;

    await page.goto("/");

    await page.getByPlaceholder("Ask FinAlly…").fill(`buy 2 ${TICKER}`);
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.getByTestId("chat-loading")).toBeVisible();
    await expect(page.getByTestId("chat-loading")).toHaveCount(0, { timeout: 10_000 });

    await expect(page.getByText(`Mock mode: executing buy 2 ${TICKER}.`)).toBeVisible();

    // The trade must actually have executed server-side regardless of how
    // the chat bubble renders it (see the inline-confirmation assertion below).
    await expect
      .poll(
        async () => {
          const portfolio = await (await request.get("/api/portfolio")).json();
          return portfolio.positions.find((p: { ticker: string }) => p.ticker === TICKER)?.quantity ?? 0;
        },
        { timeout: 10_000, message: `expected ${TICKER} position to grow by 2 shares` },
      )
      .toBe(qtyBefore + 2);

    // KNOWN APP BUG (reported to llm-engineer + frontend-engineer): the chat
    // bubble's inline confirmation renders "Failed to buy NFLX" even though
    // the trade executed (see backend/app/llm/service.py's `_execute_trades`,
    // which sets `entry["status"] = "executed"|"failed"`, against
    // frontend/components/Chat/ChatMessage.tsx's `ActionSummary`, which reads
    // `t.executed` — a boolean that's never present in the payload, so it's
    // always falsy). This assertion documents the *intended* behavior and is
    // expected to fail until the contract is fixed on one side or the other.
    await expect(page.getByText(`Bought 2 ${TICKER}`)).toBeVisible({ timeout: 5_000 });
  });
});
