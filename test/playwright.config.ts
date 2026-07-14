import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

// Fresh, throwaway SQLite file per test run so every scenario starts from
// the same seeded state (10 default tickers, $10,000 cash — PLAN.md §7).
// Deleted before the webServer boots (see globalSetup) so `init_db()` always
// re-seeds; never points at the real `db/finally.db`.
export const E2E_DB_PATH = path.resolve(__dirname, ".e2e-data/finally-e2e.db");

const BASE_URL = process.env.BASE_URL ?? "http://localhost:8000";
// The backend/frontend are already built and run elsewhere (e.g. the
// DevOps-owned test/docker-compose.test.yml container) whenever BASE_URL is
// supplied externally — only manage our own server when running locally.
const manageOwnServer = !process.env.BASE_URL;

export default defineConfig({
  testDir: "./specs",
  fullyParallel: false, // shared backend/DB state (cash, positions, watchlist) — specs must not race each other
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  globalSetup: manageOwnServer ? "./global-setup.ts" : undefined,
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: manageOwnServer
    ? {
        command: `bash -c "FINALLY_DB_PATH='${E2E_DB_PATH}' LLM_MOCK=true OPENROUTER_API_KEY=test-key MASSIVE_API_KEY= uv run uvicorn app.main:app --port 8000"`,
        cwd: path.resolve(__dirname, "../backend"),
        url: `${BASE_URL}/api/health`,
        reuseExistingServer: false,
        timeout: 60_000,
        stdout: "pipe",
        stderr: "pipe",
      }
    : undefined,
});
