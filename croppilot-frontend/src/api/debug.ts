import { API_BASE_URL } from "../config";
import { ApiError } from "./client";
import type { ApiErrorDetail, ChunkListResponse, CropListResponse, SourceListResponse } from "./types";

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

export interface ChunkFilters {
  crop_name?: string;
  source_uri?: string;
  limit?: number;
  offset?: number;
}

export function listChunks(filters: ChunkFilters = {}): Promise<ChunkListResponse> {
  const params = new URLSearchParams();
  if (filters.crop_name) params.set("crop_name", filters.crop_name);
  if (filters.source_uri) params.set("source_uri", filters.source_uri);
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return apiGet<ChunkListResponse>(`/debug/chunks${qs ? `?${qs}` : ""}`);
}

export interface SourceFilters {
  crop_name?: string;
  status?: string;
}

export function listSources(filters: SourceFilters = {}): Promise<SourceListResponse> {
  const params = new URLSearchParams();
  if (filters.crop_name) params.set("crop_name", filters.crop_name);
  if (filters.status) params.set("status", filters.status);
  const qs = params.toString();
  return apiGet<SourceListResponse>(`/debug/sources${qs ? `?${qs}` : ""}`);
}

export function listCrops(): Promise<CropListResponse> {
  return apiGet<CropListResponse>("/debug/crops");
}
