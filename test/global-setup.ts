import { execSync } from "node:child_process";
import { existsSync, mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { E2E_DB_PATH } from "./playwright.config";

const ROOT = path.resolve(__dirname, "..");
const FRONTEND_OUT = path.join(ROOT, "frontend", "out");
const BACKEND_STATIC = path.join(ROOT, "backend", "static");

/**
 * Runs once before the Playwright webServer boots (only when we're managing
 * our own server — see playwright.config.ts). Two jobs:
 *
 * 1. Make sure `backend/static` has a built frontend export to serve. This
 *    mirrors what the Dockerfile does at image-build time (PLAN.md §11); we
 *    don't touch frontend/backend source, only stage the build artifact so
 *    `main.py`'s `StaticFiles` mount has something to find.
 * 2. Delete any leftover E2E SQLite file so `init_db()` always starts from a
 *    clean, freshly-seeded database (10 default tickers, $10,000 cash).
 */
export default async function globalSetup(): Promise<void> {
  if (!existsSync(path.join(FRONTEND_OUT, "index.html"))) {
    console.log("[global-setup] frontend/out missing — running `npm run build`...");
    execSync("npm install && npm run build", {
      cwd: path.join(ROOT, "frontend"),
      stdio: "inherit",
    });
  }

  rmSync(BACKEND_STATIC, { recursive: true, force: true });
  mkdirSync(path.dirname(BACKEND_STATIC), { recursive: true });
  execSync(`cp -r "${FRONTEND_OUT}" "${BACKEND_STATIC}"`, { stdio: "inherit" });

  rmSync(E2E_DB_PATH, { force: true });
  mkdirSync(path.dirname(E2E_DB_PATH), { recursive: true });
}
