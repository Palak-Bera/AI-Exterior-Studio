"use client";

import type { RenderModeMeta } from "@/lib/types";

interface Props {
  modes: RenderModeMeta[];
  selected: string | null;
  disabled?: boolean;
  onSelect: (key: string) => void;
}

/**
 * Render-mode selection bar (Classical CV vs ControlNet AI). Unavailable modes
 * (missing diffusion deps/weights/GPU on the host) are shown disabled with a
 * tooltip.
 */
export default function RenderModeSelector({
  modes,
  selected,
  disabled,
  onSelect,
}: Props) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-white/70">Render mode</h3>
      <div className="grid gap-2 sm:grid-cols-2">
        {modes.map((m) => {
          const isActive = selected === m.key;
          const isDisabled = disabled || !m.available;
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
                      m.requires_gpu ? "a GPU / " : ""
                    }diffusion deps).`
              }
              className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                isActive
                  ? "border-emerald-400 bg-emerald-500/20"
                  : "border-white/10 bg-white/5 hover:bg-white/10"
              } ${isDisabled ? "cursor-not-allowed opacity-40" : ""}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{m.label}</span>
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
    </div>
  );
}
