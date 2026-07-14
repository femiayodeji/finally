import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// RTL's auto-cleanup only self-registers under Jest-style globals; without
// `test.globals` enabled in vitest.config.ts, each test's DOM would
// otherwise stack up across the file.
afterEach(() => {
  cleanup();
});

// Default stub so any component that fires off a fetch without an explicit
// mock in its own test fails fast and predictably instead of hanging on a
// real network call.
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: false,
    status: 501,
    statusText: "Not Implemented",
    json: async () => ({ detail: "fetch not mocked in this test" }),
  } as Response),
);
