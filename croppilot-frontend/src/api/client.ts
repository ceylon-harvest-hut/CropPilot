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
    const message =
      typeof errorBody?.detail === "string"
        ? errorBody.detail
        : `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<TResponse>;
}
