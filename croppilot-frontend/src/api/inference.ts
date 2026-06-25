import { apiPost } from "./client";
import type { AskRequest, AskResponse } from "./types";

export function askQuestion(body: AskRequest): Promise<AskResponse> {
  return apiPost<AskResponse, AskRequest>("/ask", body);
}
