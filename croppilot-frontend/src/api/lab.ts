import { apiPost } from "./client";
import { API_BASE_URL } from "../config";
import { ApiError } from "./client";
import type { ApiErrorDetail } from "./types";
import type {
  ChunkRequest,
  ChunkResponse,
  CommitRequest,
  CommitResponse,
  LabOptions,
  LoadRequest,
  LoadResponse,
} from "./types";

async function apiGet<TResponse>(path: string): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as ApiErrorDetail | null;
    const message =
      typeof errorBody?.detail === "string"
        ? errorBody.detail
        : `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<TResponse>;
}

export function getLabOptions(): Promise<LabOptions> {
  return apiGet<LabOptions>("/lab/options");
}

export function loadDocument(body: LoadRequest): Promise<LoadResponse> {
  return apiPost<LoadResponse, LoadRequest>("/lab/load", body);
}

export function chunkText(body: ChunkRequest): Promise<ChunkResponse> {
  return apiPost<ChunkResponse, ChunkRequest>("/lab/chunk", body);
}

export function commitChunks(body: CommitRequest): Promise<CommitResponse> {
  return apiPost<CommitResponse, CommitRequest>("/lab/commit", body);
}
