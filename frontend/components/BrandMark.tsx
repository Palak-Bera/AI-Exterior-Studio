"use client";

import { useState } from "react";

import { API_BASE } from "@/lib/config";

type Props = {
  /** header = full wordmark; mark = compact house icon crop via object-fit */
  variant?: "header" | "mark";
  className?: string;
};

/** Brand logo served from /storage/brand/logo.png (AES artwork). */
export default function BrandMark({ variant = "header", className }: Props) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <span
        className={
          className ||
          "inline-flex h-10 items-center gap-2 text-sm font-bold tracking-wide text-[var(--accent)]"
        }
      >
        AI EXTERIOR STUDIO
      </span>
    );
  }

  const sizeClass =
    variant === "header"
      ? "h-11 w-auto max-w-[200px] sm:h-12 sm:max-w-[240px]"
      : "h-9 w-9";

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`${API_BASE}/storage/brand/logo.png`}
      alt="AI Exterior Studio"
      className={className || `${sizeClass} object-contain`}
      onError={() => setFailed(true)}
    />
  );
}
