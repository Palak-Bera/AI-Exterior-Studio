import { API_BASE } from "./config";
import type {
  ActivateModelResponse,
  CategoriesResponse,
  CostEstimate,
  IngestResponse,
  Material,
  MaterialRateUpdate,
  ModelsResponse,
  Project,
  Region,
  RegionMaterialSelection,
  RenderModesResponse,
  RenderResponse,
  ModelStatusResponse,
  SegmentationResponse,
} from "./types";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

async function request<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  try {
    const res = await fetch(input, init);
    return handle<T>(res);
  } catch (e) {
    if (e instanceof TypeError) {
      throw new Error(
        "Cannot reach the backend at " +
          API_BASE +
          ". If you just started Docker, wait until the backend is healthy " +
          "(http://localhost:8000/health)."
      );
    }
    throw e;
  }
}

export async function uploadImage(file: File): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<IngestResponse>(`${API_BASE}/api/ingestion/upload`, {
    method: "POST",
    body: form,
  });
}

export async function getProject(projectId: string): Promise<Project> {
  return request<Project>(`${API_BASE}/api/ingestion/projects/${projectId}`, {
    cache: "no-store",
  });
}

export async function segment(
  projectId: string,
  categories: string[],
  model?: string
): Promise<SegmentationResponse> {
  return request<SegmentationResponse>(`${API_BASE}/api/segmentation/${projectId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ categories, model }),
  });
}

export async function getRegions(
  projectId: string
): Promise<SegmentationResponse> {
  return request<SegmentationResponse>(
    `${API_BASE}/api/segmentation/${projectId}/regions`,
    { cache: "no-store" }
  );
}

export async function updateRegionMask(
  projectId: string,
  category: string,
  maskDataUrl: string
): Promise<Region> {
  return request<Region>(
    `${API_BASE}/api/segmentation/${projectId}/regions/${encodeURIComponent(category)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mask_data_url: maskDataUrl }),
    }
  );
}

export async function getMaterials(): Promise<Material[]> {
  return request<Material[]>(`${API_BASE}/api/materials`, { cache: "no-store" });
}

export async function getCategories(): Promise<CategoriesResponse> {
  return request<CategoriesResponse>(`${API_BASE}/api/meta/categories`, {
    cache: "no-store",
  });
}

export async function getModels(): Promise<ModelsResponse> {
  return request<ModelsResponse>(`${API_BASE}/api/meta/models`, {
    cache: "no-store",
  });
}

export async function activateModel(model: string): Promise<ActivateModelResponse> {
  return request<ActivateModelResponse>(`${API_BASE}/api/meta/models/activate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
  });
}

export async function getRenderModes(): Promise<RenderModesResponse> {
  return request<RenderModesResponse>(`${API_BASE}/api/meta/render-modes`, {
    cache: "no-store",
  });
}

export async function getModelStatus(): Promise<ModelStatusResponse> {
  return request<ModelStatusResponse>(`${API_BASE}/api/meta/model-status`, {
    cache: "no-store",
  });
}

export async function render(
  projectId: string,
  selections: RegionMaterialSelection[],
  mode?: string
): Promise<RenderResponse> {
  return request<RenderResponse>(`${API_BASE}/api/rendering/${projectId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selections, mode: mode ?? "classical" }),
  });
}

/** Download PDF report (before/after + materials + INR cost). Triggers browser save. */
export async function downloadPdfReport(
  projectId: string,
  selections: RegionMaterialSelection[],
  outputUrl: string,
  opts?: {
    facade_width_m?: number;
    facade_height_m?: number;
    waste_factor?: number;
    include_cost?: boolean;
  }
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/reporting/${projectId}/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      selections,
      output_url: outputUrl,
      facade_width_m: opts?.facade_width_m ?? 12,
      facade_height_m: opts?.facade_height_m ?? 9,
      waste_factor: opts?.waste_factor ?? 1.1,
      include_cost: opts?.include_cost ?? true,
    }),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = /filename="?([^"]+)"?/i.exec(disposition);
  const filename = match?.[1] || "AI_Exterior_Studio_Report.pdf";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function updateMaterialRates(
  rates: MaterialRateUpdate[]
): Promise<Material[]> {
  return request<Material[]>(`${API_BASE}/api/materials/rates`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rates }),
  });
}

export async function estimateCost(
  projectId: string,
  selections: RegionMaterialSelection[],
  facadeWidthM: number,
  facadeHeightM: number,
  wasteFactor = 1.1
): Promise<CostEstimate> {
  return request<CostEstimate>(`${API_BASE}/api/costing/${projectId}/estimate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      selections,
      facade_width_m: facadeWidthM,
      facade_height_m: facadeHeightM,
      waste_factor: wasteFactor,
    }),
  });
}
