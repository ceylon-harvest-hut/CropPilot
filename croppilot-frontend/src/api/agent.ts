import { apiPost } from "./client";
import type { AskAgentRequest, AskAgentResponse } from "./types";

export function askAgent(body: AskAgentRequest): Promise<AskAgentResponse> {
  return apiPost<AskAgentResponse, AskAgentRequest>("/ask-agent", body);
}
