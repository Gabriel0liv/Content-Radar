import type {
  ContentItem,
  ContentItemListResponse,
  ContentSummary,
  DiscoveryTerm,
  GlobalSearchResponse,
  ReferenceImportJob,
  ReferenceSource,
  ReferenceSourceListResponse,
  SearchConfig,
  SearchRun,
  Transcript,
  TranscriptSegment,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Erro HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

function queryString(params: Record<string, unknown>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" || value === "Todos") return;
    query.set(key, String(value));
  });
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}

export function getContentItems(params: Record<string, unknown> = {}): Promise<ContentItemListResponse> {
  return request(`/content-items${queryString(params)}`);
}

export function getContentSummary(): Promise<ContentSummary> {
  return request("/content-items/summary");
}

export function getContentItem(id: number): Promise<ContentItem> {
  return request(`/content-items/${id}`);
}

export function updateContentItemCuration(id: number, payload: Record<string, unknown>): Promise<ContentItem> {
  return request(`/content-items/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function importYouTubeReferenceUrl(payload: {
  url: string;
  preferred_languages?: string[];
  allow_auto_captions?: boolean;
  transcription_mode?: "auto" | "max_fidelity";
}): Promise<{ reference_source_id: number | null; import_job_id: number; status: string }> {
  return request("/reference-sources/import-youtube-url", { method: "POST", body: JSON.stringify(payload) });
}

export function getReferenceSources(params: Record<string, unknown> = {}): Promise<ReferenceSourceListResponse> {
  return request(`/reference-sources${queryString(params)}`);
}

export function getReferenceSource(id: number): Promise<ReferenceSource> {
  return request(`/reference-sources/${id}`);
}

export function getReferenceImportJob(id: number): Promise<ReferenceImportJob> {
  return request(`/reference-import-jobs/${id}`);
}

export function getReferenceImportJobs(sourceId: number): Promise<ReferenceImportJob[]> {
  return request(`/reference-sources/${sourceId}/import-jobs`);
}

export function getReferenceTranscripts(sourceId: number): Promise<Transcript[]> {
  return request(`/reference-sources/${sourceId}/transcripts`);
}

export function getTranscriptSegments(transcriptId: number): Promise<TranscriptSegment[]> {
  return request(`/transcripts/${transcriptId}/segments`);
}

export function getSearchConfigs(): Promise<{ configs: SearchConfig[]; total: number }> {
  return request("/search-configs");
}

export function createSearchConfig(payload: Record<string, unknown>): Promise<SearchConfig> {
  return request("/search-configs", { method: "POST", body: JSON.stringify(payload) });
}

export function updateSearchConfig(id: number, payload: Record<string, unknown>): Promise<SearchConfig> {
  return request(`/search-configs/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function runSearchConfig(id: number): Promise<SearchRun> {
  return request(`/search-configs/${id}/run`, { method: "POST" });
}

export function getSearchConfigRuns(id: number): Promise<SearchRun[]> {
  return request(`/search-configs/${id}/runs`);
}

export function getDiscoveryTerms(q: string, limit = 20): Promise<DiscoveryTerm[]> {
  return request(`/discovery-terms${queryString({ q, limit })}`);
}

export function rebuildDiscoveryTerms(): Promise<{ rebuilt: number }> {
  return request("/discovery-terms/rebuild", { method: "POST" });
}

export function globalSearch(q: string, limit = 8): Promise<GlobalSearchResponse> {
  return request(`/global-search${queryString({ q, limit })}`);
}
