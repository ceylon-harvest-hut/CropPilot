import { apiPost } from "./client";
import type { IngestRequest, IngestResponse } from "./types";

export function ingestDocument(body: IngestRequest): Promise<IngestResponse> {
  return apiPost<IngestResponse, IngestRequest>("/ingest", body);
}
