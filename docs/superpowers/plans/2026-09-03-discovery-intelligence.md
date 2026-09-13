# Content Radar Discovery Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reference deduplication, richer YouTube metadata, topic-aware discovery, channel-relative Radar indicators, structured autocomplete, and global search while preserving the simplified Content Radar product boundary.

**Architecture:** Build on the existing FastAPI/Postgres/Next.js stack. Canonical YouTube identity and metadata enrichment come first; taxonomy/classification and channel baselines are layered on top; autocomplete and global search consume the normalized data. Classification remains hybrid and explainable, with deterministic signals first and transcript/semantic enrichment later.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, yt-dlp/YouTube metadata, Next.js 14, React 18, TypeScript, Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-09-03-discovery-intelligence-design.md`

## Global Constraints

- Keep the product boundary: `find something useful -> save/transcribe it -> record a video idea -> manually use the material elsewhere`.
- Do not reintroduce script generation, script comparison, production management, Canva, publishing, or full video creation.
- Keep official YouTube metadata clearly separate from Content Radar inferred topics.
- Preserve raw source metadata even if the classifier changes later.
- Classification must work without an LLM/semantic provider.
- Prefer deterministic, explainable ranking and confidence.
- Do not use vector embeddings in global search in this phase.
- Existing transcript fidelity behavior and simplified Ideas flow must remain compatible.
- Migrations that reconcile duplicates must not silently delete transcript data.

---

## Phase 1 — Canonical YouTube Identity and Reference Deduplication

### Task 1: Persist canonical YouTube IDs on references

**Files:**
- Modify: `src/models/reference.py`
- Modify: `src/schemas/references.py`
- Modify: `src/repositories/references_repository.py`
- Create: `alembic/versions/0011_add_reference_youtube_identity.py`
- Test: `src/test_reference_dedup.py`

**Interfaces:**
- Produces `ReferenceSource.youtube_video_id: Optional[str]`.
- Produces repository lookup `get_reference_source_by_youtube_video_id(video_id: str)`.

- [ ] **Step 1: Write failing identity tests**

Test that watch, youtu.be, shorts and embed forms all normalize to the same 11-character ID and that repository lookup returns the same source.

```python
assert extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
assert extract_youtube_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
```

- [ ] **Step 2: Add model/schema/repository field**

Add nullable `youtube_video_id` with an index first; do not add the unique constraint until duplicate reconciliation exists.

- [ ] **Step 3: Add migration 0011**

Add the column and backfill from `external_id` when `source_type='youtube_video'` and the external ID is already a valid 11-character video ID.

- [ ] **Step 4: Run tests**

```bash
python -m pytest src/test_reference_dedup.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/models/reference.py src/schemas/references.py src/repositories/references_repository.py alembic/versions/0011_add_reference_youtube_identity.py src/test_reference_dedup.py
git commit -m "feat: persist canonical youtube reference identity"
```

### Task 2: Reuse existing references during import

**Files:**
- Modify: `src/services/references_service.py`
- Modify: `src/services/youtube_reference_importer.py`
- Modify: `src/repositories/references_repository.py`
- Test: `src/test_reference_dedup.py`

**Interfaces:**
- Import of an existing YouTube ID returns/reuses the canonical source.
- Existing source with active transcript does not create a duplicate source.
- Existing source without transcript can receive a new import job.

- [ ] **Step 1: Write failing service tests**

Cover:
1. same video via two URL forms creates one source;
2. existing transcribed source is reused;
3. existing untranslated/untranscribed source gets a retry job;
4. concurrent insertion collision is recovered by re-querying the canonical ID.

- [ ] **Step 2: Implement canonical lookup before source creation**

Extract ID before creating a source and pass it through import metadata.

- [ ] **Step 3: Handle `IntegrityError` race safely**

Rollback only the failed insert, re-query by canonical ID, then continue with the existing source.

- [ ] **Step 4: Run tests and transcript regressions**

```bash
python -m pytest src/test_reference_dedup.py -v
python src/test_captions.py
```

- [ ] **Step 5: Commit**

```bash
git add src/services/references_service.py src/services/youtube_reference_importer.py src/repositories/references_repository.py src/test_reference_dedup.py
git commit -m "feat: deduplicate youtube reference imports"
```

### Task 3: Reconcile historical duplicate references and enforce uniqueness

**Files:**
- Create: `src/services/reference_reconciliation_service.py`
- Create: `src/test_reference_reconciliation.py`
- Create: `alembic/versions/0012_enforce_reference_youtube_identity.py`

**Interfaces:**
- Produces a dry-run reconciliation report.
- Canonical source keeps all safely movable transcripts/jobs.
- Ambiguous conflicts are reported, not deleted silently.

- [ ] **Step 1: Write failing reconciliation tests**

Create two duplicate sources with different transcripts and assert the service chooses one canonical row, reassigns safe children, and reports conflicts when both rows contain incompatible active transcript state.

- [ ] **Step 2: Implement deterministic canonical choice**

Priority: source with active transcript, then most transcripts, then oldest source ID.

- [ ] **Step 3: Add safe unique partial index**

After reconciliation, migration 0012 adds uniqueness for non-null `youtube_video_id` on YouTube references.

- [ ] **Step 4: Run tests**

```bash
python -m pytest src/test_reference_reconciliation.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/services/reference_reconciliation_service.py src/test_reference_reconciliation.py alembic/versions/0012_enforce_reference_youtube_identity.py
git commit -m "feat: reconcile duplicate youtube references"
```

---

## Phase 2 — Official YouTube Metadata Enrichment

### Task 4: Store category, tags and topic details on content items

**Files:**
- Modify: `src/models/content_item.py`
- Modify: `src/schemas/content_item.py`
- Modify: `src/services/content_items_service.py`
- Create: `alembic/versions/0013_add_youtube_discovery_metadata.py`
- Test: `src/test_youtube_metadata.py`

**Interfaces:**
- Adds `youtube_video_id`, `youtube_category_id`, `youtube_category_name`, `youtube_tags_json`, `youtube_topics_json`, `channel_id`.

- [ ] **Step 1: Write failing schema/ingest tests**

Verify metadata can be ingested and read without depending on `raw_json`.

- [ ] **Step 2: Add columns and Pydantic fields**

Keep raw metadata intact; normalized fields are additive.

- [ ] **Step 3: Update ingest/upsert behavior**

Normalize tags for matching while preserving original strings in JSON.

- [ ] **Step 4: Run tests**

```bash
python -m pytest src/test_youtube_metadata.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/models/content_item.py src/schemas/content_item.py src/services/content_items_service.py alembic/versions/0013_add_youtube_discovery_metadata.py src/test_youtube_metadata.py
git commit -m "feat: store youtube discovery metadata"
```

### Task 5: Add category/topic metadata helpers

**Files:**
- Create: `src/services/youtube_metadata_service.py`
- Test: `src/test_youtube_metadata.py`

**Interfaces:**
- `normalize_topic_category(value: str) -> str`
- `normalize_tag(value: str) -> str`
- `resolve_category_name(category_id: str, region_code: Optional[str]) -> Optional[str]`

- [ ] **Step 1: Write normalization tests**
- [ ] **Step 2: Implement pure normalization helpers**
- [ ] **Step 3: Implement cached category-name resolution using existing YouTube integration path/config**
- [ ] **Step 4: Run tests**
- [ ] **Step 5: Commit**

---

## Phase 3 — Taxonomy and Hybrid Classification

### Task 6: Create taxonomy and content-topic data model

**Files:**
- Create: `src/models/topic.py`
- Modify: `src/db/base.py`
- Create: `src/schemas/topics.py`
- Create: `src/repositories/topics_repository.py`
- Create: `alembic/versions/0014_add_topic_taxonomy.py`
- Test: `src/test_topics.py`

**Interfaces:**
- `Topic(type in topic|subtopic|format|series)`.
- `ContentItemTopic(confidence, source, signals_json, classifier_version)`.

- [ ] **Step 1: Write failing model/repository tests**
- [ ] **Step 2: Implement normalized topic uniqueness**

Use normalized name + type + parent identity to prevent accidental duplicates.

- [ ] **Step 3: Implement association upsert**

One current association per `(content_item_id, topic_id)`; merge evidence into `signals_json`.

- [ ] **Step 4: Add migration and seed a minimal controlled vocabulary**

Seed only foundational entries: Minecraft, Horror, Analog Horror, ARG, Hardcore, Modded Minecraft, SMP, Roleplay, Lore, Series, Challenge.

- [ ] **Step 5: Run tests and commit**

### Task 7: Implement deterministic classifier

**Files:**
- Create: `src/services/topic_classifier.py`
- Create: `src/data/topic_rules.json`
- Test: `src/test_topic_classifier.py`

**Interfaces:**
- `classify_content_item(item, channel_profile=None, transcript_text=None) -> list[TopicEvidence]`.
- `TopicEvidence` includes topic key, confidence contribution, source, signal.

- [ ] **Step 1: Write tests for Minecraft and false positives**

Cases include vague titles with strong Minecraft tags, analog-horror vocabulary, and an unrelated gaming video that only mentions Minecraft once.

- [ ] **Step 2: Implement configurable alias/rule vocabulary**

Rules live in JSON/data, not UI code.

- [ ] **Step 3: Implement confidence aggregation with negative evidence**

Keep formula deterministic and testable.

- [ ] **Step 4: Persist consolidated associations**
- [ ] **Step 5: Run tests and commit**

### Task 8: Enrich classification from transcripts

**Files:**
- Modify: `src/services/references_service.py`
- Modify: `src/services/topic_classifier.py`
- Create: `src/services/transcript_topic_enrichment.py`
- Test: `src/test_topic_classifier.py`

**Interfaces:**
- Completed transcript can trigger reclassification for linked/identifiable content item by YouTube ID.

- [ ] **Step 1: Write failing transcript enrichment test**
- [ ] **Step 2: Implement transcript evidence extraction**
- [ ] **Step 3: Reclassify without erasing manual evidence**
- [ ] **Step 4: Run transcript/classifier tests**
- [ ] **Step 5: Commit**

---

## Phase 4 — Channel Profiles and Better Radar Indicators

### Task 9: Build channel profiles

**Files:**
- Create: `src/models/channel_profile.py`
- Create: `src/repositories/channel_profiles_repository.py`
- Create: `src/services/channel_profile_service.py`
- Create: `alembic/versions/0015_add_channel_profiles.py`
- Test: `src/test_channel_profiles.py`

**Interfaces:**
- Stores sample count, dominant topics, recent views median, recent views/day median, profiling timestamp.

- [ ] **Step 1: Write median/baseline tests**
- [ ] **Step 2: Implement median calculation over recent eligible samples**
- [ ] **Step 3: Implement dominant-topic aggregation**
- [ ] **Step 4: Persist/recompute profile**
- [ ] **Step 5: Run tests and commit**

### Task 10: Add performance ratio to Radar data

**Files:**
- Modify: `src/models/content_item.py`
- Modify: `src/schemas/content_item.py`
- Modify: `src/repositories/content_items_repository.py`
- Modify: `src/services/content_items_service.py`
- Create: `alembic/versions/0016_add_radar_performance_metrics.py`
- Modify: `frontend/components/content/content-table.tsx`
- Modify: `frontend/components/content/content-filters.tsx`
- Modify: `frontend/components/content/curation-panel.tsx`
- Test: `src/test_radar_metrics.py`

**Interfaces:**
- Adds `performance_ratio`, `performance_baseline_samples`.
- Sorting supports `performance_ratio`.
- Topic/confidence filtering is available after Task 6.

- [ ] **Step 1: Write ratio/sample threshold tests**

`>=5` samples normal confidence, `2-4` low-confidence estimate, `<2` insufficient history.

- [ ] **Step 2: Implement metric calculation**
- [ ] **Step 3: Expose sort/filter API fields**
- [ ] **Step 4: Update Radar UI**

Display views, views/day, age, ratio, baseline confidence and detected topics separately from the existing score.

- [ ] **Step 5: Run backend tests and frontend build**

```bash
python -m pytest src/test_radar_metrics.py -v
cd frontend && npm run build
```

- [ ] **Step 6: Commit**

---

## Phase 5 — Structured Discovery and Autocomplete

### Task 11: Extend search configs with topic criteria

**Files:**
- Modify: `src/models/search.py`
- Modify: `src/schemas/search.py`
- Modify: `src/repositories/search_repository.py`
- Modify: `src/services/search_service.py`
- Create: `alembic/versions/0017_add_structured_discovery_filters.py`
- Test: `src/test_search_topics.py`

**Interfaces:**
- Adds included/excluded topic IDs, minimum topic confidence, minimum performance ratio.
- Reuses `youtube_categories_json` instead of replacing it.

- [ ] **Step 1: Write matching/filter tests**
- [ ] **Step 2: Add schema/model fields**
- [ ] **Step 3: Implement post-collection matching semantics**
- [ ] **Step 4: Run tests and commit**

### Task 12: Create discovery-term index and tag promotion

**Files:**
- Create: `src/models/discovery_term.py`
- Create: `src/services/discovery_terms_service.py`
- Create: `src/api/routes/discovery_terms.py`
- Modify: `src/api/main.py`
- Create: `alembic/versions/0018_add_discovery_terms.py`
- Test: `src/test_discovery_terms.py`

**Interfaces:**
- `GET /discovery-terms?q=<prefix>&limit=<n>`.
- Suggestions include type/source and relevance score.

- [ ] **Step 1: Write promotion/ranking tests**

A generic tag such as `viral` remains suppressed; a term such as `minecraft hardcore` appearing across several videos/channels can be promoted.

- [ ] **Step 2: Implement rebuild/upsert index**
- [ ] **Step 3: Implement deterministic relevance score**
- [ ] **Step 4: Expose autocomplete endpoint**
- [ ] **Step 5: Run tests and commit**

### Task 13: Add structured autocomplete to search-config UI

**Files:**
- Modify: `frontend/app/search-configs/page.tsx`
- Create: `frontend/components/search/discovery-autocomplete.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/types.ts`

**Interfaces:**
- Shows grouped suggestions: Topics, Tags, YouTube Categories, Series.
- Keeps free-text keywords available.

- [ ] **Step 1: Add API types/functions**
- [ ] **Step 2: Implement grouped autocomplete**
- [ ] **Step 3: Bind selected structured criteria to search config**
- [ ] **Step 4: Build frontend**
- [ ] **Step 5: Commit**

---

## Phase 6 — Global Search

### Task 14: Implement grouped global-search backend

**Files:**
- Create: `src/schemas/global_search.py`
- Create: `src/services/global_search_service.py`
- Create: `src/api/routes/global_search.py`
- Modify: `src/api/main.py`
- Test: `src/test_global_search.py`

**Interfaces:**
- `GET /global-search?q=<query>&limit=<n>`.
- Returns `content_items`, `references`, `transcript_matches`, `ideas`.

- [ ] **Step 1: Write ranking/group tests**

Exact title match outranks body-only match. Transcript result contains source ID, transcript ID, segment ID, times and excerpt.

- [ ] **Step 2: Implement deterministic textual search**

Use existing PostgreSQL-compatible ILIKE/full-text patterns; no vectors.

- [ ] **Step 3: Add transcript context extraction**
- [ ] **Step 4: Run tests and commit**

### Task 15: Add global-search UI and transcript deep links

**Files:**
- Create: `frontend/components/search/global-search.tsx`
- Modify: `frontend/components/layout/topbar.tsx`
- Modify: `frontend/app/references/[id]/page.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/types.ts`

**Interfaces:**
- Search is accessible globally from the shell.
- Transcript result navigates to `/references/{id}?segment=<segment_id>` and scrolls/highlights when possible.

- [ ] **Step 1: Add API client/types**
- [ ] **Step 2: Implement grouped result dropdown/panel**
- [ ] **Step 3: Implement transcript segment deep-link handling**
- [ ] **Step 4: Build frontend**
- [ ] **Step 5: Commit**

---

## Phase 7 — Series Detection and Final Integration

### Task 16: Add conservative series detection

**Files:**
- Create: `src/services/series_detection_service.py`
- Modify: `src/services/topic_classifier.py`
- Test: `src/test_series_detection.py`

**Interfaces:**
- Automatic series creation requires evidence across multiple videos unless manually confirmed.
- Series remains `Topic.type='series'`.

- [ ] **Step 1: Write positive and false-positive tests**
- [ ] **Step 2: Implement repeated-signal candidate extraction**
- [ ] **Step 3: Require multi-video evidence threshold**
- [ ] **Step 4: Persist series association and confidence**
- [ ] **Step 5: Run tests and commit**

### Task 17: End-to-end regression and documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/PORTAL_ROADMAP.md`
- Modify: `docs/reference-transcriptions.md` if import dedup behavior changes documented semantics.

- [ ] **Step 1: Run backend verification**

```bash
python -m pytest src/test_reference_dedup.py -v
python -m pytest src/test_reference_reconciliation.py -v
python -m pytest src/test_youtube_metadata.py -v
python -m pytest src/test_topics.py -v
python -m pytest src/test_topic_classifier.py -v
python -m pytest src/test_channel_profiles.py -v
python -m pytest src/test_radar_metrics.py -v
python -m pytest src/test_search_topics.py -v
python -m pytest src/test_discovery_terms.py -v
python -m pytest src/test_global_search.py -v
python -m pytest src/test_series_detection.py -v
python -m pytest src/test_ideas.py -v
python src/test_captions.py
```

- [ ] **Step 2: Run migrations on a disposable/test database**

```bash
alembic upgrade head
```

Verify duplicate reconciliation reports conflicts rather than deleting ambiguous transcript data.

- [ ] **Step 3: Run frontend production build**

```bash
cd frontend
npm run build
```

- [ ] **Step 4: Verify product boundaries**

Confirm no active UI reintroduces script generation, production workflow or Canva.

- [ ] **Step 5: Update README and roadmap**

Document canonical dedup, official-vs-inferred metadata, Radar breakout ratio, structured discovery/autocomplete, and global search.

- [ ] **Step 6: Final commit**

```bash
git add README.md docs/PORTAL_ROADMAP.md docs/reference-transcriptions.md
git commit -m "docs: document discovery intelligence workflow"
```

---

## Final Acceptance Checklist

- [ ] Same YouTube video imported through watch/youtu.be/shorts/embed resolves to one canonical reference.
- [ ] Historical duplicate reconciliation cannot silently delete transcript data.
- [ ] Content items persist category ID/name, tags, topic details and channel ID separately from raw JSON.
- [ ] Official YouTube metadata is visually/semantically distinct from inferred Content Radar topics.
- [ ] Taxonomy supports topic, subtopic, format and series.
- [ ] Minecraft/analog-horror/SMP/RP-style classification can succeed without the exact words appearing in the title.
- [ ] Classifier is deterministic without semantic/LLM fallback.
- [ ] Transcript enrichment raises confidence when relevant without erasing manual evidence.
- [ ] Channel baseline uses recent median views/day and exposes sample confidence.
- [ ] Radar can sort/filter by performance ratio and topic confidence.
- [ ] Search configs support structured topic criteria while retaining free-text keywords.
- [ ] Autocomplete groups Topics, Tags, YouTube Categories and Series and suppresses low-value generic tags.
- [ ] Global search returns Radar, Biblioteca, transcript and Ideas results.
- [ ] Transcript search result includes timestamp/segment navigation context.
- [ ] Series creation is conservative and requires multi-video evidence unless manually confirmed.
- [ ] Existing Ideas and transcript fidelity tests still pass.
- [ ] Frontend production build passes.
