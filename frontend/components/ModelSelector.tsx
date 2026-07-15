"use client";

import type { SegModelMeta } from "@/lib/types";

interface Props {
  models: SegModelMeta[];
  selected: string | null;
  disabled?: boolean;
  loading?: boolean;
  onSelect: (key: string) => void;
}

/**
 * Segmentation model bar — Grounded SAM (Grounding DINO + SAM vit-base).
 */
export default function ModelSelector({
  models,
  selected,
  disabled,
  loading,
  onSelect,
}: Props) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-white/70">Segmentation model</h3>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {models.map((m) => {
          const isActive = selected === m.key;
          const isDisabled = disabled || loading || !m.available;
          return (
            <button
              key={m.key}
              type="button"
              disabled={isDisabled}
              onClick={() => onSelect(m.key)}
              title={
                m.available
                  ? m.description
                  : `${m.label} is not available on this host (needs ${
                      m.requires_gpu ? "a GPU" : "install"
                    }${m.gated ? " + gated weights" : ""}).`
              }
              className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                isActive
                  ? "border-indigo-400 bg-indigo-500/20"
                  : "border-white/10 bg-white/5 hover:bg-white/10"
              } ${isDisabled ? "cursor-not-allowed opacity-40" : ""}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{m.label}</span>
                {m.loaded && isActive && (
                  <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] uppercase text-emerald-300">
                    Loaded
                  </span>
                )}
                {!m.available && (
                  <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] uppercase text-white/50">
                    N/A
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-xs text-white/45">{m.description}</p>
            </button>
          );
        })}
      </div>
      {loading && (
        <p className="text-xs text-indigo-300">Loading selected model into memory…</p>
      )}
    </div>
  );
}
