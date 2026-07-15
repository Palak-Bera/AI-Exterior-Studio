"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import BeforeAfter from "@/components/BeforeAfter";
import CategoryPanel from "@/components/CategoryPanel";
import CostEstimatePanel from "@/components/CostEstimatePanel";
import MaskEditor from "@/components/MaskEditor";
import MaterialPicker from "@/components/MaterialPicker";
import StudioCanvas from "@/components/StudioCanvas";
import {
  downloadPdfReport,
  getCategories,
  getMaterials,
  getModels,
  getProject,
  getRegions,
  render,
  segment,
  updateRegionMask,
} from "@/lib/api";
import type {
  CategoryMeta,
  Material,
  Project,
  Region,
  RegionMaterialSelection,
} from "@/lib/types";

type Assignment = { material_key: string; color?: string | null };

const DEFAULT_PAINT = "#1E3A5F";

function pruneAssignments(
  prev: Record<string, Assignment>,
  regionCats: Set<string>
): Record<string, Assignment> {
  const next: Record<string, Assignment> = {};
  for (const [cat, a] of Object.entries(prev)) {
    if (regionCats.has(cat)) next[cat] = a;
  }
  return next;
}

export default function StudioPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();

  const [project, setProject] = useState<Project | null>(null);
  const [categories, setCategories] = useState<CategoryMeta[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [defaults, setDefaults] = useState<string[]>([]);
  const [activeModel, setActiveModel] = useState<string | undefined>(undefined);

  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [assignments, setAssignments] = useState<Record<string, Assignment>>({});

  const [segmenting, setSegmenting] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [outputUrl, setOutputUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingMask, setEditingMask] = useState(false);
  const [savingMask, setSavingMask] = useState(false);
  const [maskRevision, setMaskRevision] = useState(0);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [facadeWidthM, setFacadeWidthM] = useState(12);
  const [facadeHeightM, setFacadeHeightM] = useState(9);

  const regionKeys = useMemo(
    () => new Set(regions.map((r) => r.category)),
    [regions]
  );
  const assignedKeys = useMemo(() => new Set(Object.keys(assignments)), [assignments]);

  useEffect(() => {
    if (!projectId) return;
    (async () => {
      try {
        const [proj, cats, mats, regs, mods] = await Promise.all([
          getProject(projectId),
          getCategories(),
          getMaterials(),
          getRegions(projectId),
          getModels(),
        ]);
        setProject(proj);
        setCategories(cats.categories);
        setDefaults(cats.default);
        setMaterials(mats);
        setRegions(regs.regions);
        setActiveModel(mods.active ?? mods.models.find((m) => m.default)?.key);
        if (regs.regions[0]) setActiveCategory(regs.regions[0].category);
      } catch {
        // Stale / missing project → go straight to upload (no error page).
        router.replace("/");
      }
    })();
  }, [projectId, router]);

  const runSegment = useCallback(async () => {
    setSegmenting(true);
    setError(null);
    setOutputUrl(null);
    setEditingMask(false);
    try {
      const res = await segment(projectId, defaults, activeModel);
      setRegions(res.regions);
      const cats = new Set(res.regions.map((r) => r.category));
      setAssignments((prev) => pruneAssignments(prev, cats));
      if (res.regions[0]) {
        setActiveCategory((prev) =>
          prev && cats.has(prev) ? prev : res.regions[0].category
        );
      } else {
        setActiveCategory(null);
        setError("No elements detected. Try a clearer, front-facing photo.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Detection failed");
    } finally {
      setSegmenting(false);
    }
  }, [projectId, defaults, activeModel]);

  const activeAssignment = activeCategory ? assignments[activeCategory] : undefined;
  const activeLabel =
    categories.find((c) => c.key === activeCategory)?.label ?? activeCategory;

  const paintColor =
    activeAssignment?.color ||
    materials.find((m) => m.key === activeAssignment?.material_key)?.default_color ||
    DEFAULT_PAINT;

  const clearAssignment = useCallback((cat: string) => {
    setAssignments((prev) => {
      const next = { ...prev };
      delete next[cat];
      return next;
    });
  }, []);

  const assignMaterial = useCallback(
    (materialKey: string) => {
      if (!activeCategory || !regionKeys.has(activeCategory)) return;
      const mat = materials.find((m) => m.key === materialKey);
      const prevColor = assignments[activeCategory]?.color;
      setAssignments((prev) => ({
        ...prev,
        [activeCategory]: {
          material_key: materialKey,
          color:
            mat?.render_path === "paint"
              ? prevColor || mat.default_color || DEFAULT_PAINT
              : null,
        },
      }));
    },
    [activeCategory, materials, regionKeys, assignments]
  );

  const setColor = useCallback(
    (color: string) => {
      if (!activeCategory) return;
      setAssignments((prev) => {
        const current = prev[activeCategory];
        if (!current) {
          return {
            ...prev,
            [activeCategory]: { material_key: "paint", color },
          };
        }
        return { ...prev, [activeCategory]: { ...current, color } };
      });
    },
    [activeCategory]
  );

  const selectionList: RegionMaterialSelection[] = useMemo(
    () =>
      Object.entries(assignments)
        .filter(([category]) => regionKeys.has(category))
        .map(([category, a]) => ({
          category,
          material_key: a.material_key,
          color: a.color,
        })),
    [assignments, regionKeys]
  );

  const runRender = useCallback(async () => {
    if (selectionList.length === 0) {
      setError("Assign finishes to one or more detected elements, then render.");
      return;
    }
    setRendering(true);
    setError(null);
    try {
      const res = await render(projectId, selectionList, "classical");
      const bust = `${res.output_url}${res.output_url.includes("?") ? "&" : "?"}t=${Date.now()}`;
      setOutputUrl(bust);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rendering failed");
    } finally {
      setRendering(false);
    }
  }, [projectId, selectionList]);

  const runPdfReport = useCallback(async () => {
    if (!outputUrl) {
      setError("Render the redesign first, then download the PDF report.");
      return;
    }
    if (selectionList.length === 0) {
      setError("No materials selected for the report.");
      return;
    }
    setPdfBusy(true);
    setError(null);
    try {
      await downloadPdfReport(projectId, selectionList, outputUrl.split("?")[0], {
        facade_width_m: facadeWidthM,
        facade_height_m: facadeHeightM,
        include_cost: true,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF report failed");
    } finally {
      setPdfBusy(false);
    }
  }, [projectId, selectionList, outputUrl, facadeWidthM, facadeHeightM]);

  const activeRegion = useMemo(
    () => regions.find((r) => r.category === activeCategory) ?? null,
    [regions, activeCategory]
  );

  const activeMeta = useMemo(
    () => categories.find((c) => c.key === activeCategory) ?? null,
    [categories, activeCategory]
  );

  const saveEditedMask = useCallback(
    async (maskDataUrl: string) => {
      if (!activeCategory) return;
      setSavingMask(true);
      setError(null);
      try {
        const updated = await updateRegionMask(projectId, activeCategory, maskDataUrl);
        setRegions((prev) => {
          const others = prev.filter((r) => r.category !== activeCategory);
          return [...others, updated];
        });
        setMaskRevision((n) => n + 1);
        setEditingMask(false);
        setOutputUrl(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to save mask");
      } finally {
        setSavingMask(false);
      }
    },
    [activeCategory, projectId]
  );

  const assignedList = useMemo(
    () => Object.entries(assignments).filter(([cat]) => regionKeys.has(cat)),
    [assignments, regionKeys]
  );

  if (!project) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div
          className="h-10 w-10 animate-spin rounded-full border-[3px] border-slate-200 border-t-[var(--accent)]"
          role="status"
          aria-label="Loading"
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">Studio</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Detect facade parts, assign finishes, then render.
          </p>
        </div>
        <Link href="/" className="btn-secondary text-sm">
          New photo
        </Link>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.9fr)]">
        <div className="space-y-4">
          <div className="glass overflow-hidden p-3 sm:p-4">
            {editingMask && activeCategory && activeMeta && !segmenting ? (
              <MaskEditor
                imageUrl={project.image_url}
                maskUrl={
                  activeRegion
                    ? `${activeRegion.mask_url}${
                        activeRegion.mask_url.includes("?") ? "&" : "?"
                      }v=${maskRevision}`
                    : null
                }
                maskColor={activeMeta.color}
                width={project.width}
                height={project.height}
                categoryLabel={activeMeta.label}
                saving={savingMask}
                onCancel={() => setEditingMask(false)}
                onSave={saveEditedMask}
              />
            ) : outputUrl && !segmenting ? (
              <BeforeAfter beforeUrl={project.image_url} afterUrl={outputUrl} />
            ) : (
              <StudioCanvas
                imageUrl={project.image_url}
                regions={regions}
                activeCategory={activeCategory}
                assignedCategories={[...assignedKeys]}
                loading={segmenting}
                loadingLabel="Detecting elements…"
              />
            )}
          </div>

          {!editingMask && (
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={runSegment}
                disabled={segmenting}
                className="btn-primary min-w-[180px]"
              >
                {segmenting ? "Detecting…" : "Detect Elements"}
              </button>
              <button
                type="button"
                disabled={!activeCategory || segmenting}
                onClick={() => {
                  setOutputUrl(null);
                  setEditingMask(true);
                }}
                className="btn-secondary"
                title={
                  activeCategory
                    ? "Refine the selected element mask with brush or eraser"
                    : "Select a detected element first"
                }
              >
                Edit mask
              </button>
              {outputUrl && (
                <button
                  type="button"
                  onClick={() => setOutputUrl(null)}
                  className="btn-secondary"
                >
                  Back to editor
                </button>
              )}
            </div>
          )}
        </div>

        <aside
          className={`glass flex flex-col gap-6 p-5 sm:p-6 ${
            editingMask ? "opacity-60 pointer-events-none" : ""
          }`}
        >
          <CategoryPanel
            categories={categories}
            regions={regions}
            activeCategory={activeCategory}
            assignedKeys={assignedKeys}
            onSelect={setActiveCategory}
            onClear={clearAssignment}
          />

          <div className="border-t border-[var(--line)] pt-5">
            <MaterialPicker
              materials={materials}
              materialKey={activeAssignment?.material_key ?? null}
              color={paintColor}
              disabled={!activeCategory || !regionKeys.has(activeCategory ?? "")}
              categoryLabel={activeCategory ? activeLabel : null}
              onMaterialChange={assignMaterial}
              onColorChange={setColor}
            />
          </div>

          {assignedList.length > 0 && (
            <div className="space-y-2 border-t border-[var(--line)] pt-4">
              <h3 className="text-sm font-semibold text-[var(--ink)]">
                Ready to render ({assignedList.length})
              </h3>
              <div className="flex flex-col gap-1.5">
                {assignedList.map(([cat, a]) => {
                  const label =
                    categories.find((c) => c.key === cat)?.label ?? cat;
                  return (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setActiveCategory(cat)}
                      className={`flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left text-xs transition ${
                        activeCategory === cat
                          ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                          : "border-[var(--line)] bg-white hover:bg-slate-50"
                      }`}
                    >
                      <span className="font-medium text-[var(--ink)]">{label}</span>
                      <span className="truncate text-[var(--muted)]">
                        {materials.find((m) => m.key === a.material_key)?.name}
                        {a.color ? ` · ${a.color}` : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <p className="text-xs leading-relaxed text-[var(--muted)]">
            Assign a finish to each element you want changed, then apply once —
            all selected masks are painted together.
          </p>

          <CostEstimatePanel
            projectId={projectId}
            selections={selectionList}
            facadeWidthM={facadeWidthM}
            facadeHeightM={facadeHeightM}
            onFacadeWidthChange={setFacadeWidthM}
            onFacadeHeightChange={setFacadeHeightM}
          />

          <button
            type="button"
            onClick={runRender}
            disabled={rendering || assignedList.length === 0}
            className="w-full rounded-xl bg-[var(--accent)] px-4 py-3.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--accent-hover)] disabled:opacity-50"
          >
            {rendering
              ? "Rendering…"
              : `Apply ${assignedList.length || ""} finish${
                  assignedList.length === 1 ? "" : "es"
                } & render`}
          </button>

          <button
            type="button"
            onClick={runPdfReport}
            disabled={pdfBusy || !outputUrl || assignedList.length === 0}
            className="w-full rounded-xl border border-[var(--line)] bg-white px-4 py-3 text-sm font-semibold text-[var(--ink)] shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
            title={
              outputUrl
                ? "Download PDF with logo, before/after, materials, and INR cost estimate"
                : "Render first to enable the PDF report"
            }
          >
            {pdfBusy ? "Generating PDF…" : "Download PDF report"}
          </button>

          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
