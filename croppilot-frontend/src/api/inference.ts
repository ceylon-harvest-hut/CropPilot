import { API_BASE_URL } from "../config";
import { apiPost } from "./client";
import type { AskRequest, AskResponse, AskTemplatesResponse } from "./types";

async function apiGet<TResponse>(path: string): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<TResponse>;
}

export function listAskTemplates(): Promise<AskTemplatesResponse> {
  return apiGet<AskTemplatesResponse>("/ask/templates");
}

export function askQuestion(body: AskRequest): Promise<AskResponse> {
  return apiPost<AskResponse, AskRequest>("/ask", body);
}
