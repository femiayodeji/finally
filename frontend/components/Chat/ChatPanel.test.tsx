import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatPanel } from "./ChatPanel";

describe("ChatPanel", () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it("renders nothing when closed", () => {
    render(<ChatPanel open={false} />);
    expect(screen.queryByText(/I'm FinAlly/)).not.toBeInTheDocument();
  });

  it("renders the welcome message when open", () => {
    render(<ChatPanel open />);
    expect(screen.getByText(/I'm FinAlly/)).toBeInTheDocument();
  });

  it("echoes the user's message, shows a loading indicator while waiting, then renders the reply", async () => {
    const user = userEvent.setup();
    let resolveFetch: (value: Response) => void = () => {};
    (global.fetch as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      }),
    );

    render(<ChatPanel open />);
    await user.type(screen.getByPlaceholderText("Ask FinAlly…"), "How's my portfolio?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getByText("How's my portfolio?")).toBeInTheDocument();
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();

    resolveFetch({
      ok: true,
      json: async () => ({
        message: "You're up 1.3% today.",
        actions: { trades: [], watchlist_changes: [] },
      }),
    } as Response);

    await waitFor(() => expect(screen.getByText("You're up 1.3% today.")).toBeInTheDocument());
    expect(screen.queryByTestId("chat-loading")).not.toBeInTheDocument();
  });

  it("shows an inline trade confirmation when the AI executes one", async () => {
    const user = userEvent.setup();
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({
        message: "Bought it.",
        actions: {
          trades: [{ ticker: "AAPL", side: "buy", quantity: 5, executed: true }],
          watchlist_changes: [],
        },
      }),
    } as Response);

    render(<ChatPanel open />);
    await user.type(screen.getByPlaceholderText("Ask FinAlly…"), "Buy 5 AAPL");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(screen.getByText(/Bought 5 AAPL/)).toBeInTheDocument());
  });
});
