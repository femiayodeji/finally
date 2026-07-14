"use client";

import { useMemo } from "react";
import type { PricePoint } from "@/lib/types";

interface SparklineProps {
  points: PricePoint[];
  positive: boolean;
  className?: string;
}

/** Full-bleed area sparkline used as a watchlist row's backdrop — price
 * action baked directly into the row rather than boxed off to one side.
 * This is the terminal's signature detail: the row itself *is* the chart. */
export function Sparkline({ points, positive, className = "" }: SparklineProps) {
  const path = useMemo(() => buildPath(points), [points]);
  if (!path) return null;

  const stroke = positive ? "var(--color-up)" : "var(--color-down)";
  const gradientId = positive ? "sparkline-up" : "sparkline-down";

  return (
    <svg
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
      viewBox="0 0 100 40"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${path} L 100 40 L 0 40 Z`} fill={`url(#${gradientId})`} stroke="none" />
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth="1"
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function buildPath(points: PricePoint[]): string | null {
  if (points.length < 2) return null;
  const prices = points.map((p) => p.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const stepX = 100 / (points.length - 1);

  return points
    .map((p, i) => {
      const x = i * stepX;
      const y = 40 - ((p.price - min) / range) * 40;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}
