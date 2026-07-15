"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { estimateCost } from "@/lib/api";
import type { CostEstimate, RegionMaterialSelection } from "@/lib/types";

type Props = {
  projectId: string;
  selections: RegionMaterialSelection[];
  facadeWidthM: number;
  facadeHeightM: number;
  onFacadeWidthChange: (v: number) => void;
  onFacadeHeightChange: (v: number) => void;
};

export default function CostEstimatePanel({
  projectId,
  selections,
  facadeWidthM,
  facadeHeightM,
  onFacadeWidthChange,
  onFacadeHeightChange,
}: Props) {
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selKey = useMemo(
    () =>
      selections
        .map((s) => `${s.category}:${s.material_key}:${s.color ?? ""}`)
        .sort()
        .join("|"),
    [selections]
  );

  useEffect(() => {
    if (selections.length === 0) {
      setEstimate(null);
      return;
    }
    let cancelled = false;
    const t = setTimeout(async () => {
      setBusy(true);
      setError(null);
      try {
        const res = await estimateCost(
          projectId,
          selections,
          facadeWidthM,
          facadeHeightM
        );
        if (!cancelled) setEstimate(res);
      } catch (e) {
        if (!cancelled) {
          setEstimate(null);
          setError(e instanceof Error ? e.message : "Estimate failed");
        }
      } finally {
        if (!cancelled) setBusy(false);
      }
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [projectId, selKey, facadeWidthM, facadeHeightM, selections]);

  return (
    <div className="space-y-3 rounded-xl border border-[var(--line)] bg-slate-50/60 p-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-[var(--ink)]">Cost estimate (₹)</h3>
        <Link
          href={`/cost?return=${encodeURIComponent(`/studio/${projectId}`)}`}
          className="text-xs font-medium text-[var(--accent)] hover:underline"
        >
          Edit rates
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs text-[var(--muted)]">
          Facade width (m)
          <input
            type="number"
            min={0.5}
            step={0.5}
            value={facadeWidthM}
            onChange={(e) => onFacadeWidthChange(Math.max(0.5, Number(e.target.value) || 0.5))}
            className="mt-1 w-full rounded-lg border border-[var(--line)] bg-white px-2 py-1.5 text-sm text-[var(--ink)]"
          />
        </label>
        <label className="text-xs text-[var(--muted)]">
          Facade height (m)
          <input
            type="number"
            min={0.5}
            step={0.5}
            value={facadeHeightM}
            onChange={(e) => onFacadeHeightChange(Math.max(0.5, Number(e.target.value) || 0.5))}
            className="mt-1 w-full rounded-lg border border-[var(--line)] bg-white px-2 py-1.5 text-sm text-[var(--ink)]"
          />
        </label>
      </div>

      {selections.length === 0 ? (
        <p className="text-xs text-[var(--muted)]">Assign finishes to see an estimate.</p>
      ) : busy && !estimate ? (
        <p className="text-xs text-[var(--muted)]">Calculating…</p>
      ) : error ? (
        <p className="text-xs text-red-600">{error}</p>
      ) : estimate ? (
        <div className="space-y-2">
          <ul className="max-h-40 space-y-1.5 overflow-y-auto text-xs">
            {estimate.lines.map((line) => (
              <li
                key={`${line.category}-${line.material_key}`}
                className="flex items-start justify-between gap-2"
              >
                <span className="text-[var(--muted)]">
                  {line.category_label}
                  <span className="block text-[10px]">
                    {line.quantity.toFixed(2)} {line.unit} × ₹
                    {line.rate_inr.toLocaleString("en-IN")}
                  </span>
                </span>
                <span className="shrink-0 font-medium tabular-nums text-[var(--ink)]">
                  ₹{line.line_total_inr.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                </span>
              </li>
            ))}
          </ul>
          <div className="flex items-center justify-between border-t border-[var(--line)] pt-2">
            <span className="text-xs font-semibold text-[var(--ink)]">Approx. total</span>
            <span className="text-sm font-bold tabular-nums text-[var(--accent)]">
              {estimate.total_display}
            </span>
          </div>
          <p className="text-[10px] leading-relaxed text-[var(--muted)]">
            Rates from the Cost page · approximate visual estimate only
          </p>
        </div>
      ) : null}
    </div>
  );
}
