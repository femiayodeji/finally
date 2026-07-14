import type { NextConfig } from "next";

// Static export served by FastAPI, same origin, single port (PLAN.md §3/§11).
const nextConfig: NextConfig = {
  output: "export",
  images: {
    // Next.js image optimization requires a server; not available in a
    // static export (PLAN.md §3 — single container, single port).
    unoptimized: true,
  },
  typescript: {
    // Next 16.2.10's built-in type-check worker throws
    // "The id argument must be of type string. Received undefined" against
    // typescript@7.0.2 (the newer native compiler) — an incompatibility, not
    // a real type error (verified: `tsc --noEmit` passes clean standalone).
    // Type safety is enforced instead via a `tsc --noEmit` pre-build step
    // (see package.json `build` script) that runs the real TS7 compiler
    // directly, bypassing Next's broken integration.
    ignoreBuildErrors: true,
  },
  async rewrites() {
    // Dev-only convenience: proxies /api/* to the FastAPI backend on :8000
    // so `next dev` can talk to a locally-running server without CORS.
    // Ignored in the static export (`next build`/`next export`) — in prod
    // FastAPI serves the export and /api/* directly, same-origin (PLAN.md §10).
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
