import type { Config } from "tailwindcss";

// Locked design tokens — 01-UI-SPEC.md "Color" table + "Suggested Tailwind
// token names". `up` / `down` / `ink-dim` are aliases required by
// frontend/lib/format.ts (directionColorClass returns text-up/text-down/text-ink-dim).
const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0d1117",
        panel: "#1a1a2e",
        "border-muted": "#30363d",
        "accent-blue": "#209dd7",
        "accent-yellow": "#ecad0a",
        "accent-purple": "#753991", // reserved, unused Phase 1
        positive: "#3fb950",
        negative: "#f85149",
        neutral: "#8b949e",
        // Aliases so frontend/lib/format.ts's text-up/text-down/text-ink-dim resolve.
        up: "#3fb950",
        down: "#f85149",
        "ink-dim": "#8b949e",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        panel: "6px",
      },
    },
  },
  plugins: [],
};

export default config;
