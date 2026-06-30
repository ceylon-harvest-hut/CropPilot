/** Mirrors app/domains/ingestion/schemas.py */
export interface IngestRequest {
  source_uri: string;
  crop_name: string;
}

export interface IngestResponse {
  source_id: number;
  chunk_count: number;
  status: string;
}

/** Mirrors app/domains/inference/schemas.py */
export type AskTemplateName = "context_only" | "hybrid";

export interface AskRequest {
  question: string;
  crop_name: string;
  template?: AskTemplateName | null;
}

export interface PromptTemplateOption {
  name: AskTemplateName;
  label: string;
  description: string;
}

export interface AskTemplatesResponse {
  templates: PromptTemplateOption[];
  default_template: AskTemplateName;
}

export interface ReferenceDocumentResponse {
  source_uri: string;
  crop_name: string;
  title: string;
  excerpt: string;
  source_type: SourceType;
}

export interface AskResponse {
  answer: string;
  references: ReferenceDocumentResponse[];
  template: AskTemplateName;
}

/** Mirrors app/domains/agent/schemas.py */
export interface AskAgentRequest {
  question: string;
}

export interface ToolCallResponse {
  name: string;
  arguments: Record<string, unknown>;
  result: string;
}

export interface AskAgentResponse {
  answer: string;
  tools_used: ToolCallResponse[];
}

export interface ApiErrorDetail {
  detail:
    | string
    | { loc: string[]; msg: string; type: string }[]
    | { message: string; [key: string]: unknown };
}

/** Mirrors app/domains/lab/schemas.py */
export type SourceType = "file" | "web_url";

export interface LoaderOption {
  name: string;
  label: string;
  source_types: SourceType[];
}

export interface ChunkerOption {
  name: string;
  label: string;
}

export interface LabOptions {
  source_types: SourceType[];
  loaders: LoaderOption[];
  chunkers: ChunkerOption[];
  embedders: string[];
}

export interface LoadRequest {
  source_uri: string;
  source_type: SourceType;
  loader: string;
}

export interface DocumentItem {
  text: string;
  metadata: Record<string, unknown>;
}

export interface LoadResponse {
  documents: DocumentItem[];
  source_uri: string;
  source_type: string;
  loader: string;
  media_type: string;
  char_count: number;
  line_count: number;
}

export interface ChunkRequest {
  documents: DocumentItem[];
  crop_name: string;
  chunker: string;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface ChunkItem {
  index: number;
  section_name: string;
  page_number: number;
  char_count: number;
  text: string;
}

export interface ChunkResponse {
  chunk_count: number;
  chunks: ChunkItem[];
}

export interface CommitRequest {
  source_uri: string;
  crop_name: string;
  chunks: ChunkItem[];
  embedder: string;
  replace_existing?: boolean;
}

export interface CommitResponse {
  source_id: number;
  chunk_count: number;
  status: string;
  replaced: boolean;
  previous_chunk_count: number;
}

export interface SourceExistsResponse {
  exists: boolean;
  source_id?: number | null;
  chunk_count?: number | null;
  status?: string | null;
  crop_names: string[];
}

/** Mirrors app/domains/debug/schemas.py */
export interface StoredChunk {
  chunk_id: string;
  crop_tag: string;
  source_uri: string;
  section_name: string;
  page_number: number;
  text_preview: string;
}

export interface ChunkListResponse {
  total: number;
  limit: number;
  offset: number;
  chunks: StoredChunk[];
}

export interface SourceItem {
  source_id: number;
  origin_url: string;
  status: string;
  crop_names: string[];
}

export interface SourceListResponse {
  total: number;
  limit: number;
  offset: number;
  sources: SourceItem[];
}

export interface CropItem {
  crop_id: number;
  name: string;
  botanical_name: string | null;
}

export interface CropListResponse {
  total: number;
  crops: CropItem[];
}

/** Mirrors app/domains/debug/schemas.py graph responses */
export interface GraphCropSummary {
  name: string;
  node_count: number;
  source_uris: string[];
}

export interface GraphCropListResponse {
  total: number;
  crops: GraphCropSummary[];
}

export interface GraphFertilizer {
  fertilizer: string;
  apply_start_weeks_after_planting: number | null;
  repeat_count: number | null;
  repeat_interval_weeks: number | null;
  quantity_kg_per_ha: number | null;
}

export interface GraphPest {
  name: string;
  impact: string | null;
  solution: string | null;
}

export interface GraphDisease {
  name: string;
  causal_agent: string | null;
  impact: string | null;
  solution: string | null;
}

export interface GraphCropNode {
  source_uri: string;
  name: string;
  manifest_crop_name: string | null;
  scientific_name: string | null;
  altitude_min_m: number | null;
  altitude_max_m: number | null;
  temp_min_c: number | null;
  temp_max_c: number | null;
  rainfall_min_mm: number | null;
  rainfall_max_mm: number | null;
  ph_min: number | null;
  ph_max: number | null;
  pit_length_cm: number | null;
  pit_width_cm: number | null;
  row_distance_cm: number | null;
  plant_distance_cm: number | null;
  expected_harvest_kg_per_ha: number | null;
  days_to_maturity: number | null;
  nursery_period_days: number | null;
  seed_amount_per_ha: number | null;
  seed_metric_type: string | null;
  growing_areas: string[];
  growing_seasons: string[];
  varieties: string[];
  soil_types: string[];
  fertilizer_schedule: GraphFertilizer[];
  pests: GraphPest[];
  diseases: GraphDisease[];
}

export interface GraphCropDetailResponse {
  name: string;
  nodes: GraphCropNode[];
}
