"use client";

import type { CategoryMeta, Region } from "@/lib/types";

interface Props {
  categories: CategoryMeta[];
  regions: Region[];
  activeCategory: string | null;
  assignedKeys: Set<string>;
  onSelect: (category: string) => void;
  onClear?: (category: string) => void;
}

/** Detected elements stacked full-width (horizontal stretch). */
export default function CategoryPanel({
  categories,
  regions,
  activeCategory,
  assignedKeys,
  onSelect,
  onClear,
}: Props) {
  const detected = new Set(regions.map((r) => r.category));
  const detectedCats = categories.filter((c) => detected.has(c.key));

  if (detectedCats.length === 0) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-[var(--ink)]">Detected elements</h3>
        <p className="rounded-xl border border-dashed border-[var(--line)] bg-slate-50 px-4 py-6 text-center text-sm text-[var(--muted)]">
          Run Detect Elements to find walls, windows, gates, and more.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-[var(--ink)]">Detected elements</h3>
        <span className="text-xs text-[var(--muted)]">
          {assignedKeys.size}/{detectedCats.length} finished
        </span>
      </div>
      <p className="text-xs text-[var(--muted)]">
        Select an element below, then choose a finish. Each row stretches full width.
      </p>
      <div className="flex flex-col gap-2">
        {detectedCats.map((cat) => {
          const isActive = activeCategory === cat.key;
          const hasMaterial = assignedKeys.has(cat.key);
          return (
            <div
              key={cat.key}
              className={`flex w-full items-stretch overflow-hidden rounded-xl border transition ${
                isActive
                  ? "border-[var(--accent)] bg-[var(--accent-soft)] shadow-sm"
                  : hasMaterial
                    ? "border-[var(--accent)]/40 bg-[var(--accent-soft)]/70"
                    : "border-[var(--line)] bg-white hover:border-slate-300"
              }`}
            >
              <button
                type="button"
                onClick={() => onSelect(cat.key)}
                className="flex min-w-0 flex-1 items-center gap-3 px-4 py-3.5 text-left"
              >
                <span
                  className="h-3.5 w-3.5 shrink-0 rounded-full ring-2 ring-white"
                  style={{ background: cat.color }}
                />
                <span className="flex-1 truncate text-sm font-medium text-[var(--ink)]">
                  {cat.label}
                </span>
                {hasMaterial ? (
                  <span className="rounded-full bg-[var(--accent)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                    Set
                  </span>
                ) : (
                  <span className="text-xs text-[var(--muted)]">Choose finish →</span>
                )}
              </button>
              {hasMaterial && onClear && (
                <button
                  type="button"
                  title={`Clear finish for ${cat.label}`}
                  onClick={() => onClear(cat.key)}
                  className="border-l border-[var(--line)] px-3 text-sm text-[var(--muted)] hover:bg-red-50 hover:text-red-600"
                >
                  ×
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
