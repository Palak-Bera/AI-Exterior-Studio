"use client";

import { useEffect, useMemo, useState } from "react";

import { mediaUrl } from "@/lib/config";
import type { Material } from "@/lib/types";

export const DARK_PAINT_PRESETS = [
  "#1E3A5F",
  "#0F2747",
  "#1A0A2E",
  "#3B0A1A",
  "#1B3A2F",
  "#3D1F0A",
  "#4A0E2C",
  "#1C2833",
  "#2C1608",
  "#0D2137",
  "#4A3728",
  "#2E4057",
];

const GROUP_ORDER = ["paint", "cladding", "tiles", "patterns"] as const;
type GroupKey = (typeof GROUP_ORDER)[number] | string;

const GROUP_LABELS: Record<string, string> = {
  paint: "Paint",
  cladding: "Cladding",
  tiles: "Tiles",
  patterns: "Patterns",
};

interface Props {
  materials: Material[];
  materialKey: string | null;
  color: string;
  disabled: boolean;
  categoryLabel?: string | null;
  onMaterialChange: (key: string) => void;
  onColorChange: (color: string) => void;
}

function clampDarkRich(hex: string): string {
  const h = hex.replace("#", "");
  if (h.length !== 6) return "#1E3A5F";
  let r = parseInt(h.slice(0, 2), 16) / 255;
  let g = parseInt(h.slice(2, 4), 16) / 255;
  let b = parseInt(h.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let s = max === 0 ? 0 : (max - min) / max;
  let v = max;
  if (v > 0.55) {
    const scale = 0.55 / v;
    r *= scale;
    g *= scale;
    b *= scale;
  }
  if (s < 0.35 && v > 0.05) {
    const mid = (r + g + b) / 3;
    const boost = 0.35 / Math.max(s, 0.01);
    r = mid + (r - mid) * Math.min(boost, 2.2);
    g = mid + (g - mid) * Math.min(boost, 2.2);
    b = mid + (b - mid) * Math.min(boost, 2.2);
  }
  const to = (x: number) =>
    Math.max(0, Math.min(255, Math.round(x * 255)))
      .toString(16)
      .padStart(2, "0");
  return `#${to(r)}${to(g)}${to(b)}`.toUpperCase();
}

function groupOf(m: Material): GroupKey {
  return m.group || (m.render_path === "paint" ? "paint" : "texture");
}

/**
 * Finish picker: choose one type tab, then only that catalog is shown (no long scroll).
 */
export default function MaterialPicker({
  materials,
  materialKey,
  color,
  disabled,
  categoryLabel,
  onMaterialChange,
  onColorChange,
}: Props) {
  const groups = useMemo(() => {
    const map = new Map<string, Material[]>();
    for (const m of materials) {
      const g = groupOf(m);
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(m);
    }
    return GROUP_ORDER.filter((k) => map.has(k)).map((k) => ({
      key: k,
      label: GROUP_LABELS[k] ?? k,
      items: map.get(k)!,
    }));
  }, [materials]);

  const selectedGroup = useMemo(() => {
    const m = materials.find((x) => x.key === materialKey);
    return m ? groupOf(m) : null;
  }, [materials, materialKey]);

  const [activeTab, setActiveTab] = useState<string>("paint");

  useEffect(() => {
    if (selectedGroup) setActiveTab(selectedGroup);
    else if (groups[0]) setActiveTab(groups[0].key);
  }, [selectedGroup, groups]);

  const active = groups.find((g) => g.key === activeTab) ?? groups[0];
  const showingPaint = active?.key === "paint";

  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-sm font-semibold text-[var(--ink)]">
          Finish
          {categoryLabel ? (
            <span className="font-normal text-[var(--muted)]"> — {categoryLabel}</span>
          ) : null}
        </h3>
        {!categoryLabel ? (
          <p className="mt-1 text-xs text-[var(--muted)]">Select a detected element first.</p>
        ) : (
          <p className="mt-1 text-xs text-[var(--muted)]">
            Pick a finish type, then choose one option below.
          </p>
        )}
      </div>

      {/* Type selector — full-width horizontal stretch */}
      <div className="grid grid-cols-2 gap-1.5 rounded-xl border border-[var(--line)] bg-slate-50 p-1.5 sm:grid-cols-4">
        {groups.map((g) => {
          const isOn = active?.key === g.key;
          return (
            <button
              key={g.key}
              type="button"
              disabled={disabled}
              onClick={() => setActiveTab(g.key)}
              className={`rounded-lg px-2 py-2 text-xs font-semibold transition ${
                isOn
                  ? "bg-white text-[var(--ink)] shadow-sm ring-1 ring-[var(--line)]"
                  : "text-[var(--muted)] hover:text-[var(--ink)]"
              } ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
            >
              {g.label}
            </button>
          );
        })}
      </div>

      {/* Only the selected type’s options */}
      <div className="min-h-[200px] rounded-xl border border-[var(--line)] bg-white p-3">
        {!active ? (
          <p className="py-8 text-center text-sm text-[var(--muted)]">No finishes available.</p>
        ) : showingPaint ? (
          <div className="space-y-3">
            <button
              type="button"
              disabled={disabled}
              onClick={() => onMaterialChange("paint")}
              className={`w-full rounded-lg border px-3 py-2.5 text-left text-sm font-medium ${
                materialKey === "paint"
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[var(--line)] hover:bg-slate-50"
              } ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
            >
              Solid paint (dark / rich)
            </button>
            <p className="text-[11px] text-[var(--muted)]">Choose a darker, richer color:</p>
            <div className="flex flex-wrap gap-2">
              {DARK_PAINT_PRESETS.map((c) => (
                <button
                  key={c}
                  type="button"
                  disabled={disabled}
                  title={c}
                  onClick={() => {
                    onMaterialChange("paint");
                    onColorChange(c);
                  }}
                  className={`h-8 w-8 rounded-lg border-2 shadow-sm ${
                    materialKey === "paint" && color.toUpperCase() === c.toUpperCase()
                      ? "border-[var(--ink)]"
                      : "border-white"
                  }`}
                  style={{ background: c }}
                />
              ))}
            </div>
            <div className="flex items-center gap-2 pt-1">
              <label className="text-xs text-[var(--muted)]">Custom</label>
              <input
                type="color"
                value={color}
                disabled={disabled}
                onChange={(e) => {
                  onMaterialChange("paint");
                  onColorChange(clampDarkRich(e.target.value));
                }}
                className="h-8 w-12 cursor-pointer rounded border border-[var(--line)] bg-white"
              />
              <span className="font-mono text-[11px] text-[var(--muted)]">{color}</span>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            {active.items.map((m) => {
              const on = materialKey === m.key;
              return (
                <button
                  key={m.key}
                  type="button"
                  disabled={disabled}
                  title={m.name}
                  onClick={() => onMaterialChange(m.key)}
                  className={`overflow-hidden rounded-lg border text-left transition ${
                    on
                      ? "border-[var(--accent)] ring-2 ring-[var(--accent)]/25"
                      : "border-[var(--line)] hover:border-slate-300"
                  } ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
                >
                  <div className="aspect-square bg-slate-100">
                    {m.texture_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={mediaUrl(m.texture_url)}
                        alt={m.name}
                        className="h-full w-full object-cover"
                      />
                    ) : null}
                  </div>
                  <div className="truncate px-2 py-1 text-[10px] font-medium text-[var(--ink)]">
                    {m.name.replace(/^Wall |^Texture /i, "")}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
