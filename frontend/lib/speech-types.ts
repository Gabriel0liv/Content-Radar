export type SpeechOperation = "stt" | "tts";
export type SpeechJobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type SpeechJob = {
  id: number;
  operation: SpeechOperation;
  status: SpeechJobStatus;
  stage: string;
  progress_percent: number;
  progress_message: string | null;
  requested_config_json: Record<string, unknown>;
  resolved_config_json: Record<string, unknown> | null;
  result_json: Record<string, any> | null;
  reference_source_id: number | null;
  transcript_id: number | null;
  retry_of_job_id: number | null;
  worker_id: string | null;
  error_code: string | null;
  error_message: string | null;
  archived_at: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  updated_at: string;
};

export type SpeechArtifact = {
  id: number;
  speech_job_id: number;
  artifact_type: string;
  filename: string;
  mime_type: string | null;
  size_bytes: number | null;
  created_at: string;
};

export type SpeechSpeakerMapping = {
  raw_speaker: string;
  display_name: string;
};

export type SpeechStatus = {
  mode: "native";
  queue: { queued: number; running: number };
  worker: {
    online: boolean;
    worker_id: string | null;
    last_heartbeat_at: string | null;
    capabilities: Record<string, any> | null;
  };
};

export type SpeechDashboardJob = {
  id: number;
  operation: SpeechOperation;
  status: SpeechJobStatus;
  stage: string;
  progress_percent: number;
  label: string;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  finished_at: string | null;
};

export type SpeechDashboard = {
  transcriptions_today: number;
  tts_today: number;
  total_jobs: number;
  jobs_completed: number;
  jobs_failed: number;
  success_rate: number;
  available_voices: number;
  storage_used_bytes: number;
  queue: { queued: number; running: number };
  recent_jobs: SpeechDashboardJob[];
  active_job: SpeechDashboardJob | null;
  system_health: {
    worker_online: boolean;
    cuda: boolean;
    gpu_name: string | null;
    ffmpeg: boolean;
    espeak: boolean;
    whisperx: boolean;
    diarization: boolean;
    hf_token_configured: boolean;
    tts_engines: Array<Record<string, any> | string>;
  };
};

export type SpeechCapabilities = {
  worker_online: boolean;
  worker_id: string | null;
  last_heartbeat_at: string | null;
  capabilities: Record<string, any>;
};

export type DiagnosticCheck = {
  id: string;
  status: "ok" | "warning" | "error" | string;
  reason: string;
  action?: string | null;
};

export type SpeechDiagnostics = SpeechCapabilities & {
  diagnostics: {
    status: string;
    checks: DiagnosticCheck[];
  };
};

export type SpeechVoice = {
  id: string;
  engine: "kokoro" | "piper";
  engine_voice_id: string;
  display_name: string;
  language: string;
  locale: string;
  gender?: string;
  style?: string;
  source_type: string;
  available: boolean;
  unavailable_reason?: string | null;
  sample_state?: string;
  sample_storage_key?: string | null;
};

export type SpeechPreset = {
  id?: number | string;
  name: string;
  operation: SpeechOperation;
  description?: string | null;
  config?: Record<string, any>;
  config_json?: Record<string, any>;
  is_builtin?: boolean;
};

export type SpeechSettings = {
  default_stt_preset: string;
  default_language: string | null;
  default_diarization: boolean;
  default_tts_engine: "kokoro" | "piper";
  default_voice: string | null;
  default_output_format: "wav" | "mp3";
  default_ptbr_normalization: boolean;
  default_export_formats: string[];
  offline_mode: boolean;
  artifact_retention_days: number;
  input_retention_days: number;
  retain_debug_artifacts: boolean;
  hardware_policy: "auto" | "cuda" | "cpu";
  hf_token_configured: boolean;
};

export type SttUploadOptions = {
  preset: string;
  language?: string;
  diarization: boolean;
  num_speakers?: number;
  min_speakers?: number;
  max_speakers?: number;
  quiet_speech: boolean;
  initial_prompt?: string;
  reference_source_id?: number;
  model?: string;
  device?: "auto" | "cuda" | "cpu";
  compute_type?: "int8" | "float16" | "float32";
  batch_size?: number;
  vad_onset?: number;
  vad_offset?: number;
  chunk_size?: number;
  diarize_model?: string;
  offline?: boolean;
  cache_dir?: string;
  export_formats?: string[];
};

export type TtsRequest = {
  text: string;
  engine: "kokoro" | "piper";
  voice: string;
  output_format: "wav" | "mp3";
  speed: number;
  language: string;
  normalize_ptbr: boolean;
  analyze_ptbr: boolean;
  preset?: string;
  preview_chars?: number;
};
