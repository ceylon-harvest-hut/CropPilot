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
export interface AskRequest {
  question: string;
  crop_name?: string | null;
}

export interface SourceChunkResponse {
  chunk_id: string;
  section_name: string;
  text_preview: string;
}

export interface AskResponse {
  answer: string;
  sources: SourceChunkResponse[];
}

export interface ApiErrorDetail {
  detail: string | { loc: string[]; msg: string; type: string }[];
}

/** Mirrors app/domains/lab/schemas.py */
export interface LabOptions {
  loaders: string[];
  chunkers: string[];
  embedders: string[];
}

export interface LoadRequest {
  source_uri: string;
  loader: string;
}

export interface DocumentItem {
  text: string;
  metadata: Record<string, unknown>;
}

export interface LoadResponse {
  documents: DocumentItem[];
  source_uri: string;
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
}

export interface CommitResponse {
  source_id: number;
  chunk_count: number;
  status: string;
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
