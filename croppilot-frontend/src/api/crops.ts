import { API_BASE_URL } from "../config";
import { ApiError } from "./client";
import type { ApiErrorDetail, CropListResponse } from "./types";

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

/** Returns crops that have at least one indexed knowledge source (searchable via /ask). */
export function listIndexedCrops(): Promise<CropListResponse> {
  return apiGet<CropListResponse>("/crops");
}
