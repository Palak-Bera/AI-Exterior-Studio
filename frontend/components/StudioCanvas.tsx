"use client";

import { mediaUrl } from "@/lib/config";
import type { Region } from "@/lib/types";

interface Props {
  imageUrl: string;
  regions: Region[];
  activeCategory: string | null;
  assignedCategories?: string[];
  /** Show a circular loader over the image (e.g. while Detect Elements runs). */
  loading?: boolean;
  loadingLabel?: string;
}

export default function StudioCanvas({
  imageUrl,
  regions,
  activeCategory,
  assignedCategories = [],
  loading = false,
  loadingLabel = "Detecting elements…",
}: Props) {
  const assigned = new Set(assignedCategories);
  const visible = loading
    ? []
    : regions.filter(
        (r) => r.category === activeCategory || assigned.has(r.category)
      );

  return (
    <div className="relative overflow-hidden rounded-xl border border-[var(--line)] bg-slate-100">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={mediaUrl(imageUrl)}
        alt="house"
        className={`block w-full transition ${loading ? "opacity-60" : ""}`}
      />
      {visible.map((region) => {
        const isActive = region.category === activeCategory;
        return (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={region.id}
            src={mediaUrl(region.mask_url)}
            alt={`${region.category} mask`}
            className={`pointer-events-none absolute inset-0 h-full w-full mix-blend-multiply ${
              isActive ? "opacity-55" : "opacity-30"
            }`}
          />
        );
      })}
      {loading && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white/55 backdrop-blur-[2px]">
          <div
            className="h-12 w-12 animate-spin rounded-full border-[3px] border-slate-200 border-t-[var(--accent)]"
            role="status"
            aria-label={loadingLabel}
          />
          <p className="text-sm font-medium text-[var(--ink)]">{loadingLabel}</p>
        </div>
      )}
    </div>
  );
}
