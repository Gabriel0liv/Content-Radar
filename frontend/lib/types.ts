export type ContentStatus = "new" | "reviewed" | "selected" | "rejected" | "produced" | "archived";

export interface DetectedTopic {
  id: number;
  name: string;
  type: string;
  confidence: number;
  source: string;
}

export interface ContentItem {
  id: number;
  source: string;
  external_id: string;
  content_type: string;
  title: string;
  description: string | null;
  url: string;
  channel_title: string | null;
  channel_id: string | null;
  youtube_video_id: string | null;
  youtube_category_id: string | null;
  youtube_category_name: string | null;
  youtube_tags_json: string[];
  youtube_topics_json: string[];
  topic_classification_version: string | null;
  performance_ratio: number | null;
  performance_baseline_samples: number;
  published_at: string | null;
  views: number;
  likes: number;
  comments: number;
  views_per_day: number;
  score: number;
  topic_seed: string | null;
  discovery_query: string | null;
  language: string | null;
  country_code: string | null;
  status: ContentStatus;
  notes: string | null;
  raw_json: Record<string, unknown> | null;
  reviewed_at: string | null;
  selected_at: string | null;
  rejected_reason: string | null;
  production_notes: string | null;
  collected_at: string;
  last_seen_at: string;
  detected_topics: DetectedTopic[];
}

export interface ContentItemListResponse {
  items: ContentItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ContentSummary {
  total_items: number;
  new_items: number;
  items_by_source: Record<string, number>;
  max_score: number;
  max_views: number;
}

export type ReferenceSourceStatus = "new" | "importing" | "transcribed" | "needs_audio_transcription" | "failed" | "archived";

export interface ReferenceSource {
  id: number;
  source_type: string;
  source_url: string;
  external_id: string | null;
  youtube_video_id?: string | null;
  title: string;
  channel_title: string | null;
  channel_id: string | null;
  description: string | null;
  published_at: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  like_count: number | null;
  thumbnail_url: string | null;
  language: string | null;
  status: ReferenceSourceStatus;
  notes: string | null;
  raw_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ReferenceSourceListResponse {
  items: ReferenceSource[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReferenceImportRawResult extends Record<string, unknown> {
  version_number?: number | string;
  same_hash_as_previous?: boolean;
}

export interface ReferenceImportJob {
  id: number;
  reference_source_id: number | null;
  source_url: string;
  status: "queued" | "running" | "completed" | "failed" | "needs_audio_transcription";
  method: string;
  preferred_languages: string[] | null;
  selected_language: string | null;
  selected_caption_type: string | null;
  error_message: string | null;
  raw_result_json: ReferenceImportRawResult | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface Transcript {
  id: number;
  reference_source_id: number;
  import_job_id: number | null;
  language: string | null;
  source_method: string;
  full_text: string;
  full_text_hash: string;
  srt_text: string | null;
  vtt_text: string | null;
  raw_json: Record<string, unknown> | null;
  created_at: string;
  version_number: number;
  is_active: boolean;
  duplicate_of_transcript_id: number | null;
}

export interface TranscriptSegment {
  id: number;
  transcript_id: number;
  segment_index: number;
  start_time: number | null;
  end_time: number | null;
  speaker: string | null;
  text: string;
  tokens_json: Record<string, unknown> | null;
  created_at: string;
}

export interface SearchConfig {
  id: number;
  name: string;
  description: string | null;
  status: "active" | "paused" | "archived";
  language: string | null;
  country_code: string | null;
  region_code: string | null;
  days_back: number | null;
  min_views: number | null;
  max_results_per_query: number | null;
  sources_json: string[];
  keywords_json: string[];
  negative_keywords_json: string[];
  youtube_categories_json: string[];
  included_topic_ids: number[];
  excluded_topic_ids: number[];
  minimum_topic_confidence: number | null;
  minimum_performance_ratio: number | null;
  created_at: string;
  updated_at: string;
}

export interface SearchRun {
  id: number;
  search_config_id: number;
  status: "queued" | "running" | "completed" | "failed";
  trigger_source: string;
  started_at: string | null;
  finished_at: string | null;
  items_found: number;
  items_inserted: number;
  items_updated: number;
  error_message: string | null;
  raw_summary_json?: Record<string, unknown> | null;
  created_at: string;
}

export interface DiscoveryTerm {
  id: number;
  normalized_term: string;
  display_name: string;
  type: "topic" | "subtopic" | "format" | "series" | "tag" | "youtube_category" | string;
  entity_id: number | null;
  usage_count: number;
  video_count: number;
  channel_count: number;
  relevance_score: number;
  last_seen_at: string | null;
}

export interface GlobalSearchResponse {
  query: string;
  content_items: Array<{ id: number; title: string; url: string; source: string; channel_title: string | null; performance_ratio: number | null; match_rank: number }>;
  references: Array<{ id: number; title: string; source_url: string; channel_title: string | null; match_rank: number }>;
  transcript_matches: Array<{ reference_source_id: number; transcript_id: number; segment_id: number; video_title: string; start_time: number | null; end_time: number | null; matched_excerpt: string; match_rank: number }>;
  ideas: Array<{ id: number; title: string; description: string | null; niche: string | null; status: string; match_rank: number }>;
}

export type CaseRadarPlatform = "youtube" | "x" | "tiktok" | "instagram" | "reddit" | "web";
export type CaseRadarRunStatus = "queued" | "running" | "completed" | "partially_completed" | "failed" | "cancelled";
export type ResearchCaseStatus = "researching" | "ready" | "approved" | "rejected" | "duplicate" | "already_used";

export interface CaseResearchCreatePayload {
  theme: string;
  desired_usable_cases: number;
  languages: string[];
  platforms: CaseRadarPlatform[];
  date_from?: string | null;
  date_to?: string | null;
  include_terms?: string[];
  exclude_terms?: string[];
  priorities?: string[];
  exclusions?: string[];
  research_depth: "quick" | "balanced" | "deep";
  provider_budgets?: Partial<Record<CaseRadarPlatform, number>>;
  global_result_budget: number;
}

export interface ProviderCoverageEntry {
  results?: number;
  requests?: number;
  method?: string | null;
  available?: boolean;
  errors?: Array<{ code?: string; message?: string; provider?: string | null }>;
}

export interface CaseResearchRun {
  id: number;
  status: CaseRadarRunStatus;
  stage: string;
  progress_percent: number;
  progress_message: string | null;
  request_json: CaseResearchCreatePayload;
  provider_coverage_json: Record<string, ProviderCoverageEntry>;
  discovered_candidates: number;
  clustered_cases: number;
  usable_cases: number;
  rejected_cases: number;
  worker_id: string | null;
  errors_json: Array<Record<string, unknown>>;
  result_summary_json: Record<string, unknown> | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  updated_at: string;
}

export interface CaseResearchRunListResponse {
  items: CaseResearchRun[];
  total: number;
  limit: number;
  offset: number;
}

export interface CaseResearchQuery {
  id: number;
  run_id: number;
  language: string;
  target_platform: string | null;
  query_text: string;
  intent: string;
  status: string;
  result_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchSource {
  id: number;
  run_id: number;
  query_id: number | null;
  platform: CaseRadarPlatform;
  external_id: string | null;
  canonical_url: string;
  author_handle: string | null;
  author_display_name: string | null;
  title_or_caption: string | null;
  text: string | null;
  published_at: string | null;
  discovered_at: string;
  media_type: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  language: string | null;
  engagement_json: Record<string, unknown>;
  hashtags_json: string[];
  relation_json: Record<string, unknown> | null;
  discovery_method: string;
  source_confidence: number;
  content_item_id: number | null;
  reference_source_id: number | null;
}

export interface DossierSource {
  id: number;
  platform?: string;
  url?: string;
  canonical_url?: string;
  title?: string | null;
  title_or_caption?: string | null;
  author?: string | null;
  author_handle?: string | null;
  published_at?: string | null;
  role?: string | null;
  confidence?: number | null;
}

export interface DossierClaim {
  id: number;
  text: string;
  claim_type?: string | null;
  status: string;
  confidence: number;
  evidence_ids: number[];
  supporting_evidence_ids: number[];
  contradicting_evidence_ids: number[];
}

export interface CaseDossier {
  case_id: number;
  title: string;
  summary: string | null;
  what_happens: string | null;
  primary_source: DossierSource | null;
  earliest_known_source: DossierSource | null;
  likely_original_source: DossierSource | null;
  sources: DossierSource[];
  verified_context: DossierClaim[];
  unverified_claims: DossierClaim[];
  contradictions: DossierClaim[];
  alternative_explanations: DossierClaim[];
  useful_social_context: Array<Record<string, unknown>>;
  transcript_segments: Array<Record<string, unknown>>;
  evidence: Array<Record<string, unknown>>;
  origin_status: "unknown" | "likely" | "confirmed";
  provenance_confidence: number;
  research_confidence: number;
  provider_coverage: Record<string, ProviderCoverageEntry>;
  dossier_version: number;
}

export interface ResearchCase {
  id: number;
  run_id: number;
  provisional_title: string;
  normalized_summary: string | null;
  status: ResearchCaseStatus;
  alleged_date: string | null;
  alleged_location: string | null;
  earliest_known_date: string | null;
  origin_status: "unknown" | "likely" | "confirmed";
  origin_confidence: number;
  research_confidence: number;
  likely_original_source_id: number | null;
  earliest_known_source_id: number | null;
  selected_primary_source_id: number | null;
  dossier_version: number;
  dossier_json: CaseDossier | null;
  manual_notes: string | null;
  already_used: boolean;
  created_at: string;
  updated_at: string;
}
