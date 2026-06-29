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
