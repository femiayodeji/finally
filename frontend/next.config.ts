import type { NextConfig } from "next";

// Static export is required for production (the Dockerfile copies
// `frontend/out` into the backend image, see PLAN.md §11). Next.js does not
// allow `rewrites` alongside `output: "export"`, so both are gated on the
// build mode: `next build` runs with NODE_ENV=production and produces the
// static export; `next dev` runs with NODE_ENV=development and instead
// proxies /api/* to a locally running backend so the app can be developed
// against `uv run uvicorn app.main:app --port 8000` without a CORS setup.
const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = isProd
  ? { output: "export" }
  : {
      async rewrites() {
        return [
          {
            source: "/api/:path*",
            destination: "http://localhost:8000/api/:path*",
          },
        ];
      },
    };

export default nextConfig;
