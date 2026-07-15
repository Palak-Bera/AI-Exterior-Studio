"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { getMaterials, updateMaterialRates } from "@/lib/api";
import { mediaUrl } from "@/lib/config";
import type { Material } from "@/lib/types";

function formatInr(n: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n || 0);
}

type Draft = { rate_inr: string; unit: "sqm" | "unit" };

function safeReturnPath(raw: string | null): string | null {
  if (!raw) return null;
  // Only allow internal studio return paths
  if (raw.startsWith("/studio/") && !raw.includes("//") && !raw.includes("..")) {
    return raw;
  }
  return null;
}

function CostPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = safeReturnPath(searchParams.get("return"));

  const [materials, setMaterials] = useState<Material[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const mats = await getMaterials();
      setMaterials(mats);
      const next: Record<string, Draft> = {};
      for (const m of mats) {
        next[m.key] = {
          rate_inr: String(m.rate_inr ?? 0),
          unit: m.unit === "unit" ? "unit" : "sqm",
        };
      }
      setDrafts(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load materials");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const groups = useMemo(() => {
    const map = new Map<string, Material[]>();
    for (const m of materials) {
      const g = m.group_label || m.group || "Other";
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(m);
    }
    return Array.from(map.entries());
  }, [materials]);

  const goBack = () => {
    if (returnTo) {
      router.push(returnTo);
      return;
    }
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
      return;
    }
    router.push("/");
  };

  const save = async () => {
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const rates = materials.map((m) => {
        const d = drafts[m.key];
        return {
          key: m.key,
          rate_inr: Math.max(0, Number(d?.rate_inr || 0)),
          unit: (d?.unit === "unit" ? "unit" : "sqm") as "sqm" | "unit",
        };
      });
      await updateMaterialRates(rates);
      setMessage("Rates saved in Indian Rupees (₹). Studio estimates will use these prices.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={goBack}
            className="mb-3 inline-flex items-center gap-1.5 text-sm font-medium text-[var(--accent)] hover:underline"
          >
            <span aria-hidden>←</span>
            Back to {returnTo ? "studio" : "previous page"}
          </button>
          <p className="text-sm font-semibold uppercase tracking-wider text-[var(--accent)]">
            Costing
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--ink)]">
            Material rates (₹ INR)
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
            Set unit prices for each finish. The studio cost engine multiplies these
            rates by approximate area from detected masks (calibrated by facade size).
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={goBack}
            className="rounded-xl border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-medium text-[var(--ink)] hover:bg-slate-50"
          >
            Back
          </button>
          <Link
            href="/"
            className="rounded-xl border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-medium text-[var(--ink)] hover:bg-slate-50"
          >
            Home
          </Link>
          <button
            type="button"
            onClick={save}
            disabled={saving || loading}
            className="rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save rates"}
          </button>
        </div>
      </div>

      {message && (
        <p className="rounded-xl border border-[var(--accent)]/25 bg-[var(--accent-soft)] px-4 py-3 text-sm text-[var(--accent)]">
          {message}
        </p>
      )}
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-[var(--muted)]">Loading materials…</p>
      ) : (
        <div className="space-y-8">
          {groups.map(([label, items]) => (
            <section key={label} className="glass overflow-hidden">
              <div className="border-b border-[var(--line)] bg-slate-50/80 px-5 py-3">
                <h2 className="text-sm font-semibold text-[var(--ink)]">{label}</h2>
              </div>
              <div className="divide-y divide-[var(--line)]">
                {items.map((m) => {
                  const draft = drafts[m.key] || { rate_inr: "0", unit: "sqm" as const };
                  return (
                    <div
                      key={m.key}
                      className="flex flex-wrap items-center gap-4 px-5 py-4"
                    >
                      <div className="flex min-w-[12rem] flex-1 items-center gap-3">
                        {m.texture_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={mediaUrl(m.texture_url)}
                            alt=""
                            className="h-10 w-10 rounded-lg object-cover"
                          />
                        ) : (
                          <span
                            className="h-10 w-10 rounded-lg border border-[var(--line)]"
                            style={{ background: m.default_color || "#1E3A5F" }}
                          />
                        )}
                        <div>
                          <p className="text-sm font-medium text-[var(--ink)]">{m.name}</p>
                          <p className="text-xs text-[var(--muted)]">{m.key}</p>
                        </div>
                      </div>

                      <label className="flex items-center gap-2 text-sm">
                        <span className="text-[var(--muted)]">Unit</span>
                        <select
                          value={draft.unit}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [m.key]: {
                                ...draft,
                                unit: e.target.value === "unit" ? "unit" : "sqm",
                              },
                            }))
                          }
                          className="rounded-lg border border-[var(--line)] bg-white px-2 py-1.5 text-sm"
                        >
                          <option value="sqm">₹ / sq.m</option>
                          <option value="unit">₹ / piece</option>
                        </select>
                      </label>

                      <label className="flex items-center gap-2 text-sm">
                        <span className="text-[var(--muted)]">Rate</span>
                        <span className="font-medium text-[var(--ink)]">₹</span>
                        <input
                          type="number"
                          min={0}
                          step={1}
                          value={draft.rate_inr}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [m.key]: { ...draft, rate_inr: e.target.value },
                            }))
                          }
                          className="w-28 rounded-lg border border-[var(--line)] bg-white px-2 py-1.5 text-sm tabular-nums"
                        />
                      </label>

                      <p className="w-28 text-right text-xs text-[var(--muted)]">
                        {formatInr(Number(draft.rate_inr) || 0)}
                        {draft.unit === "unit" ? "/pc" : "/m²"}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CostPage() {
  return (
    <Suspense
      fallback={<p className="text-sm text-[var(--muted)]">Loading cost page…</p>}
    >
      <CostPageInner />
    </Suspense>
  );
}
