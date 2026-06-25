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
