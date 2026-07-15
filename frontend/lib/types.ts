export interface Project {
  id: string;
  filename: string;
  image_url: string;
  width: number;
  height: number;
  status: string;
  created_at: string;
}

export interface IngestWarning {
  code: string;
  message: string;
}

export interface IngestResponse {
  project: Project;
  warnings: IngestWarning[];
}

export interface Region {
  id: string;
  project_id: string;
  category: string;
  instance_count: number;
  mask_url: string;
  polygons: number[][][];
  pixel_area: number;
  confidence: number;
}

export interface SegmentationResponse {
  project_id: string;
  backend: string;
  regions: Region[];
}

export interface Material {
  key: string;
  name: string;
  render_path: "paint" | "texture";
  default_color: string | null;
  texture_url: string | null;
  group?: string;
  group_label?: string;
  rate_inr?: number;
  unit?: "sqm" | "unit";
  currency?: string;
}

export interface MaterialRateUpdate {
  key: string;
  rate_inr: number;
  unit: "sqm" | "unit";
}

export interface CostLine {
  category: string;
  category_label: string;
  material_key: string;
  material_name: string;
  quantity: number;
  unit: string;
  rate_inr: number;
  line_total_inr: number;
  color?: string | null;
}

export interface CostEstimate {
  currency: string;
  currency_symbol: string;
  facade_width_m: number;
  facade_height_m: number;
  facade_area_m2: number;
  waste_factor: number;
  lines: CostLine[];
  subtotal_inr: number;
  total_inr: number;
  total_display: string;
  disclaimer: string;
}

export interface CategoryMeta {
  key: string;
  label: string;
  color: string;
}

export interface CategoriesResponse {
  default: string[];
  categories: CategoryMeta[];
}

export interface SegModelMeta {
  key: string;
  label: string;
  description: string;
  default: boolean;
  requires_gpu: boolean;
  gated: boolean;
  available: boolean;
  loaded?: boolean;
  active?: boolean;
}

export interface ModelsResponse {
  models: SegModelMeta[];
  active?: string | null;
}

export interface ActivateModelResponse {
  model: string;
  loaded: boolean;
  active: boolean;
  load_seconds: number;
  label: string;
}

export interface RenderModeMeta {
  key: string;
  label: string;
  description: string;
  default: boolean;
  requires_gpu: boolean;
  available: boolean;
}

export interface RenderModesResponse {
  modes: RenderModeMeta[];
}

export interface ModelStatusResponse {
  ready: boolean;
  status: "ready" | "partial" | "downloading" | "pending" | "failed" | "missing";
  message: string;
  models_dir?: string;
  groups_requested?: string[];
  current_group?: string | null;
  groups?: Record<string, string>;
  core_models_ready?: boolean;
}

export interface RegionMaterialSelection {
  category: string;
  material_key: string;
  color?: string | null;
}

export interface RenderResponse {
  project_id: string;
  input_url: string;
  output_url: string;
  backend: string;
  applied: RegionMaterialSelection[];
}
