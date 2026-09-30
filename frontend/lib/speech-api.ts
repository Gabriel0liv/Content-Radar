import type {
  SpeechArtifact,
  SpeechCapabilities,
  SpeechDiagnostics,
  SpeechJob,
  SpeechOperation,
  SpeechPreset,
  SpeechSettings,
  SpeechSpeakerMapping,
  SpeechStatus,
  SpeechVoice,
  SttUploadOptions,
  TtsRequest,
} from "@/lib/speech-types";

export const SPEECH_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${SPEECH_API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail || body || {});
    throw new Error(detail || `Erro HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

function json<T>(path: string, method: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function append(form: FormData, key: string, value: unknown) {
  if (value === undefined || value === null || value === "") return;
  if (Array.isArray(value)) form.append(key, value.join(","));
  else form.append(key, String(value));
}

export const speechApi = {
  getStatus: () => request<SpeechStatus>("/speech/status"),
  getCapabilities: () => request<SpeechCapabilities>("/speech/capabilities"),
  getDiagnostics: () => request<SpeechDiagnostics>("/speech/diagnostics"),
  getSettings: () => request<SpeechSettings>("/speech/settings"),
  updateSettings: (changes: Partial<SpeechSettings>) => json<SpeechSettings>("/speech/settings", "PUT", changes),

  listJobs: (params?: { operation?: SpeechOperation; status?: string; includeArchived?: boolean; limit?: number }) => {
    const query = new URLSearchParams();
    query.set("limit", String(params?.limit ?? 100));
    if (params?.operation) query.set("operation", params.operation);
    if (params?.status) query.set("status", params.status);
    if (params?.includeArchived) query.set("include_archived", "true");
    return request<SpeechJob[]>(`/speech/jobs?${query}`);
  },
  getJob: (id: number) => request<SpeechJob>(`/speech/jobs/${id}`),
  cancelJob: (id: number) => json<SpeechJob>(`/speech/jobs/${id}/cancel`, "POST"),
  retryJob: (id: number) => json<SpeechJob>(`/speech/jobs/${id}/retry`, "POST"),
  archiveJob: (id: number) => json<{ id: number; archived: boolean; transcript_id: number | null }>(`/speech/jobs/${id}/archive`, "POST"),

  listArtifacts: (jobId: number) => request<SpeechArtifact[]>(`/speech/jobs/${jobId}/artifacts`),
  artifactDownloadUrl: (jobId: number, artifactId: number) => `${SPEECH_API_BASE_URL}/speech/jobs/${jobId}/artifacts/${artifactId}/download`,
  deleteArtifact: (jobId: number, artifactId: number) => request<{ id: number; deleted: boolean }>(`/speech/jobs/${jobId}/artifacts/${artifactId}`, { method: "DELETE" }),

  listSpeakerMappings: (jobId: number) => request<SpeechSpeakerMapping[]>(`/speech/jobs/${jobId}/speaker-mappings`),
  setSpeakerMapping: (jobId: number, rawSpeaker: string, displayName: string) =>
    json<SpeechSpeakerMapping>(`/speech/jobs/${jobId}/speaker-mappings/${encodeURIComponent(rawSpeaker)}`, "PUT", { display_name: displayName }),

  uploadStt: (file: File, options: SttUploadOptions) => {
    const form = new FormData();
    form.append("file", file);
    append(form, "preset", options.preset);
    append(form, "language", options.language);
    append(form, "diarization", options.diarization);
    append(form, "num_speakers", options.num_speakers);
    append(form, "min_speakers", options.min_speakers);
    append(form, "max_speakers", options.max_speakers);
    append(form, "quiet_speech", options.quiet_speech);
    append(form, "initial_prompt", options.initial_prompt);
    append(form, "reference_source_id", options.reference_source_id);
    append(form, "model", options.model);
    append(form, "device", options.device);
    append(form, "compute_type", options.compute_type);
    append(form, "batch_size", options.batch_size);
    append(form, "vad_onset", options.vad_onset);
    append(form, "vad_offset", options.vad_offset);
    append(form, "chunk_size", options.chunk_size);
    append(form, "diarize_model", options.diarize_model);
    append(form, "offline", options.offline);
    append(form, "cache_dir", options.cache_dir);
    append(form, "export_formats", options.export_formats);
    return request<SpeechJob>("/speech/jobs/stt/upload", { method: "POST", body: form });
  },

  createTts: (payload: TtsRequest, preview = false) => json<SpeechJob>(preview ? "/speech/jobs/tts/preview" : "/speech/jobs/tts", "POST", payload),
  analyzeText: (text: string, language = "pt-br") => json<{ success: boolean; language: string; analysis: Record<string, any> }>("/speech/tts/analyze-text", "POST", { text, language }),

  listVoices: async () => (await request<{ voices: SpeechVoice[] }>("/speech/voices")).voices,
  voiceSampleUrl: (voiceId: string) => `${SPEECH_API_BASE_URL}/speech/voices/${encodeURIComponent(voiceId)}/sample`,
  createVoiceSample: (voiceId: string, text?: string) => json<SpeechJob>(`/speech/jobs/tts/voice-samples/${encodeURIComponent(voiceId)}`, "POST", { text: text || null }),
  createAllVoiceSamples: (text?: string) => json<SpeechJob[]>("/speech/jobs/tts/voice-samples", "POST", { text: text || null }),
  createVoiceCompare: (text: string, voiceIds?: string[]) => json<SpeechJob>("/speech/jobs/tts/voice-compare", "POST", { text, voice_ids: voiceIds || null, language: "pt-br", markdown_report: true }),

  listPresets: async (operation: SpeechOperation) => (await request<{ presets: SpeechPreset[] }>(`/speech/presets?operation=${operation}`)).presets,
  createPreset: (payload: { name: string; operation: SpeechOperation; config: Record<string, any>; description?: string }) => json<SpeechPreset>("/speech/presets", "POST", payload),
  updatePreset: (id: number, payload: { name?: string; config?: Record<string, any>; description?: string }) => json<SpeechPreset>(`/speech/presets/${id}`, "PATCH", payload),
  deletePreset: (id: number) => request<void>(`/speech/presets/${id}`, { method: "DELETE" }),
};
