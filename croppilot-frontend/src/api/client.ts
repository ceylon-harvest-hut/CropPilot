import { API_BASE_URL } from "../config";
import type { ApiErrorDetail } from "./types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function formatApiErrorDetail(detail: ApiErrorDetail["detail"]): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail === "object" && !Array.isArray(detail) && "message" in detail) {
    return String((detail as { message: string }).message);
  }
  return "Request failed";
}

export async function apiPost<TResponse, TBody>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as ApiErrorDetail | null;
    const message = errorBody?.detail
      ? formatApiErrorDetail(errorBody.detail)
      : `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<TResponse>;
}
