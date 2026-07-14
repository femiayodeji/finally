const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactCurrencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

export function formatCurrency(value: number): string {
  return currencyFormatter.format(value);
}

/** Same as formatCurrency but drops trailing .00 — used for share quantities
 * and other spots where cents rarely matter to the eye. */
export function formatCurrencyCompact(value: number): string {
  return compactCurrencyFormatter.format(value);
}

export function formatSigned(value: number, formatter: (v: number) => string): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatter(value)}`;
}

export function formatPercent(value: number, digits = 2): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

export function formatQuantity(value: number): string {
  // Fractional shares are supported server-side; trim to at most 4 dp and
  // strip trailing zeros so whole-share trades still read as "10" not "10.0000".
  return value % 1 === 0 ? value.toFixed(0) : value.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

/** Accepts either an ISO timestamp string or a unix-seconds/ms number and
 * normalizes to a Date. Backend timestamps (§6/§8) are unix seconds. */
export function toDate(value: number | string): Date {
  if (typeof value === "string") return new Date(value);
  // Heuristic: values above ~1e12 are already milliseconds.
  return new Date(value > 1e12 ? value : value * 1000);
}

export function formatTime(value: number | string): string {
  return toDate(value).toLocaleTimeString("en-US", { hour12: false });
}

export function directionColorClass(direction: "up" | "down" | "flat" | null | undefined): string {
  if (direction === "up") return "text-up";
  if (direction === "down") return "text-down";
  return "text-ink-dim";
}
