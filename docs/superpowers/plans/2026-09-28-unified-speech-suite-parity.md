# Unified Speech Suite Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the native Content Radar Speech Suite so `/audio` fully replaces day-to-day use of the old Speech Studio for STT, TTS, voices/models, presets, diagnostics, history and Biblioteca integration.

**Architecture:** Extend the existing PostgreSQL-backed `speech_jobs` foundation instead of creating a second speech application. Keep validation, durable state, presets, artifact delivery and user-facing normalization in FastAPI/PostgreSQL; keep WhisperX/pyannote/FFmpeg/Torch/Piper/Kokoro and hardware/model discovery inside `speech_worker`. Build one native Next.js `/audio` workspace with internal sections over the common speech API.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Next.js/React/TypeScript, WhisperX/faster-whisper, pyannote, FFmpeg, Piper, Kokoro, pytest.

**Spec:** `docs/superpowers/specs/2026-09-28-unified-speech-suite-parity-design.md`

## Global Constraints

- `master` remains the primary branch; implementation uses short-lived feature branches and is squash-merged after verification.
- Do not introduce a second frontend, iframe, proxy-to-Speech-Studio runtime, SQLite speech history, Redis or Celery.
- The main API must not import Torch, WhisperX, pyannote or heavy TTS engine libraries.
- Heavy STT/TTS work must use the persistent PostgreSQL `speech_jobs` queue/lease/heartbeat system.
- Raw diarization speaker labels remain immutable; display mappings are separate data.
- Browser-facing APIs never expose unrestricted local filesystem URLs.
- Secrets such as Hugging Face tokens are never returned by API responses.
- Built-in presets are immutable through normal user CRUD.
- Preserve the existing STT implementation and regression behavior while extending it.
- Runtime acceptance requires real STT and TTS smoke coverage; compile/build-only evidence is insufficient.

## Review Focus

- Unsupported or misleading file extension: server rejects invalid STT input based on validated type/path rules rather than trusting a filename.
- Worker capability changes after job creation: queued jobs fail cleanly with normalized capability errors instead of crashing or hanging.
- Cancellation during a heavy stage: cancellation becomes durable and releases/cleans temporary state without marking a partial artifact completed.
- Missing optional runtime pieces (HF access, Piper/Kokoro assets, FFmpeg/eSpeak): UI/API expose actionable unavailable capability states instead of generic 500s.
- Artifact/history deletion with transcript or Biblioteca references: referenced durable data is never silently destroyed.

---

## File structure and ownership

### Existing files extended

- `src/models/speech.py` — durable speech jobs, presets, artifacts, mappings and worker capability state.
- `src/repositories/speech_jobs.py` — speech queue/history/preset/artifact persistence.
- `src/schemas/speech.py` — engine-neutral STT/TTS option models and preset types.
- `src/schemas/speech_jobs.py` — API/job read and create schemas.
- `src/services/speech_jobs_service.py` — job creation, validation, resolved config and history actions.
- `src/services/speech_storage.py` — safe staged input/artifact storage.
- `src/services/speech_result_importer.py` — completed STT import into transcript/Biblioteca structures.
- `src/api/routes/speech.py` — lightweight speech metadata/capability routes.
- `src/api/routes/speech_jobs.py` — durable STT/TTS job routes.
- `speech_worker/worker.py` — common claim/execute/finalize loop.
- `frontend/components/layout/sidebar.tsx` — one global `Áudio` entry.
- `.github/workflows/case-radar-ci.yml` — speech regression and non-heavy verification.
- `README.md` — local speech setup, runtime and smoke instructions.

### New backend/worker units

- `src/services/speech_presets_service.py` — native built-in/personal STT/TTS preset CRUD/resolution.
- `src/services/speech_assets_service.py` — safe artifact/sample metadata and download resolution.
- `src/services/speech_capabilities_service.py` — API read model over worker capability state.
- `src/services/speech_settings_service.py` — non-secret persisted speech settings and secret-presence status.
- `speech_worker/tts/__init__.py`
- `speech_worker/tts/base.py`
- `speech_worker/tts/registry.py`
- `speech_worker/tts/piper_engine.py`
- `speech_worker/tts/kokoro_engine.py`
- `speech_worker/tts/ptbr_text.py`
- `speech_worker/tts/text_chunking.py`
- `speech_worker/tts/runner.py` — job-oriented TTS orchestration/progress/artifact production.
- `speech_worker/runtime/capabilities.py` — normalized hardware/dependency/model/voice discovery.
- `speech_worker/runtime/diagnostics.py` — explicit diagnostic checks and safe status payload.
- `scripts/speech_stt_smoke.py`
- `scripts/speech_tts_smoke.py`

### New frontend units

- `frontend/app/audio/page.tsx` — `/audio` route.
- `frontend/components/audio/audio-workspace.tsx` — section navigation and page state.
- `frontend/components/audio/audio-overview.tsx`
- `frontend/components/audio/transcription-panel.tsx`
- `frontend/components/audio/transcription-result.tsx`
- `frontend/components/audio/tts-panel.tsx`
- `frontend/components/audio/history-panel.tsx`
- `frontend/components/audio/presets-panel.tsx`
- `frontend/components/audio/voices-models-panel.tsx`
- `frontend/components/audio/diagnostics-panel.tsx`
- `frontend/components/audio/settings-panel.tsx`
- `frontend/lib/speech-api.ts` — typed browser API client for Speech Suite.
- `frontend/lib/speech-types.ts` — UI-facing speech DTO types.

---

### Task 1: Complete the durable speech domain and migrations

**Files:**
- Modify: `src/models/speech.py`
- Modify: `src/schemas/speech.py`
- Modify: `src/schemas/speech_jobs.py`
- Modify: `src/repositories/speech_jobs.py`
- Create: `alembic/versions/0022_complete_speech_suite_foundation.py`
- Modify/Test: `src/test_speech_job_models.py`
- Modify/Test: `src/test_speech_job_repository.py`

**Interfaces:**
- Consumes: existing `SpeechJob`, `SpeechPreset`, `SpeechArtifact`, `SpeechSpeakerMapping`, `SpeechWorkerState`.
- Produces: typed TTS create/read payloads, artifact/sample metadata, preset CRUD persistence, retry/archive-safe history primitives and worker capability data required by later tasks.

- [ ] **Step 1: Write failing model/repository tests** for TTS job payload persistence, preset operation uniqueness, artifact lookup by job/type, speaker mapping immutability, history filtering and safe retry source metadata.
- [ ] **Step 2: Run** `python -m pytest -q src/test_speech_job_models.py src/test_speech_job_repository.py` and confirm the new assertions fail.
- [ ] **Step 3: Add the minimal schema/model/repository fields and methods** needed by the tests; create migration `0022` rather than mutating `0019`/`0020`/`0021`.
- [ ] **Step 4: Add the Review Focus persistence tests** proving referenced transcript/artifact relationships are not cascade-destroyed by ordinary history operations.
- [ ] **Step 5: Run** the two tests plus `alembic upgrade head` against a disposable database; expected PASS and migration reaches `0022`.
- [ ] **Step 6: Commit** `feat: complete Speech Suite persistence foundation`.

### Task 2: Native preset and settings services

**Files:**
- Create: `src/services/speech_presets_service.py`
- Create: `src/services/speech_settings_service.py`
- Modify: `src/services/speech_jobs_service.py`
- Modify: `src/api/routes/speech.py`
- Test: `src/test_speech_presets.py`
- Create/Test: `src/test_speech_settings_service.py`

**Interfaces:**
- Consumes: Task 1 `SpeechPreset` persistence.
- Produces: `list_presets(operation)`, `create_preset(...)`, `update_preset(...)`, `delete_preset(...)`, `resolve_stt_preset(...)`, `resolve_tts_preset(...)`, `get_speech_settings()`, `update_speech_settings(...)`.

- [ ] **Step 1: Write failing tests** for built-in STT presets `fast`, `balanced`, `maximum_quality`, personal STT/TTS CRUD, duplicate names by operation, built-in immutability and secret-presence-only settings.
- [ ] **Step 2: Run** `python -m pytest -q src/test_speech_presets.py src/test_speech_settings_service.py`; expected FAIL on missing native CRUD/settings behavior.
- [ ] **Step 3: Implement services and lightweight routes** without importing heavy runtime libraries.
- [ ] **Step 4: Test invalid preset configs** and verify API returns validation errors rather than persisting unusable settings.
- [ ] **Step 5: Run tests** and confirm PASS.
- [ ] **Step 6: Commit** `feat: add native Speech presets and settings`.

### Task 3: Finish STT configuration parity and upload validation

**Files:**
- Modify: `src/schemas/speech.py`
- Modify: `src/schemas/speech_jobs.py`
- Modify: `src/services/speech_jobs_service.py`
- Modify: `src/services/speech_storage.py`
- Modify: `src/api/routes/speech_jobs.py`
- Modify/Test: `src/test_speech_jobs_service.py`
- Modify/Test: `src/test_speech_api.py`
- Modify/Test: `src/test_speech_storage.py`

**Interfaces:**
- Consumes: Task 2 preset resolver.
- Produces: complete STT job request with model/device/compute/batch/VAD/chunk/diarization/offline/export options and safe staged input validation.

- [ ] **Step 1: Write failing API/service tests** for all guided and advanced STT options and resolved configuration inspection.
- [ ] **Step 2: Add failing upload tests** for allowed MP3/WAV/MP4/MKV/MOV/M4A/WEBM, path traversal filenames, unsupported extensions and mismatched/invalid staged input cases.
- [ ] **Step 3: Run targeted tests** and confirm failures.
- [ ] **Step 4: Extend schemas/service/storage/API** so filenames are sanitized, storage paths are generated by the service, and worker-facing resolved config is authoritative.
- [ ] **Step 5: Run** `python -m pytest -q src/test_speech_storage.py src/test_speech_jobs_service.py src/test_speech_api.py`; expected PASS.
- [ ] **Step 6: Commit** `feat: complete STT request and upload parity`.

### Task 4: Preserve and extend STT runtime, subtitles and speaker mapping

**Files:**
- Modify: `speech_worker/stt/*` as required by current structure
- Modify: `src/services/speech_result_importer.py`
- Modify: `speech_worker/worker.py`
- Modify/Test: `src/test_speech_stt_engine.py`
- Modify/Test: `src/test_speech_stt_normalize.py`
- Modify/Test: `src/test_speech_subtitles.py`
- Modify/Test: `src/test_speech_result_importer.py`
- Create/Test: `src/test_speech_speaker_mapping.py`

**Interfaces:**
- Consumes: Task 3 resolved STT config.
- Produces: normalized transcript with immutable raw speaker labels, derived TXT/JSON/SRT/VTT artifacts, display-name mapping support and completed transcript/Biblioteca import metadata.

- [ ] **Step 1: Write failing tests** for advanced VAD/chunk/offline config reaching the STT runner and for cancellation checks between heavy stages.
- [ ] **Step 2: Write subtitle tests** for two-line maximum, readable line target, min/max duration, speaker-change boundary and valid SRT/VTT timestamps.
- [ ] **Step 3: Write speaker-mapping tests** proving display names change rendered/exported views while raw `SPEAKER_XX` metadata remains unchanged.
- [ ] **Step 4: Run targeted STT tests** and confirm new cases fail.
- [ ] **Step 5: Implement the minimal runtime/import/export changes** and durable cancellation cleanup.
- [ ] **Step 6: Run existing + new STT regression tests**; expected PASS with no loss of current transcription behavior.
- [ ] **Step 7: Commit** `feat: complete STT runtime and speaker mapping parity`.

### Task 5: Port the TTS engine abstraction into the speech worker

**Files:**
- Create: `speech_worker/tts/__init__.py`
- Create: `speech_worker/tts/base.py`
- Create: `speech_worker/tts/registry.py`
- Create: `speech_worker/tts/piper_engine.py`
- Create: `speech_worker/tts/kokoro_engine.py`
- Create: `speech_worker/tts/ptbr_text.py`
- Create: `speech_worker/tts/text_chunking.py`
- Test: `src/test_speech_tts_registry.py`
- Test: `src/test_speech_tts_text.py`
- Test: `src/test_speech_tts_chunking.py`

**Interfaces:**
- Consumes: legacy Speech Studio TTS behavior as reference only.
- Produces: `TTSEngine` interface, `TTSRegistry`, normalized voice descriptors, `analyze_ptbr_text(text)`, `normalize_ptbr_text(text)`, `chunk_text(text, ...)` and engine-neutral synthesize calls.

- [ ] **Step 1: Write failing unit tests** for registry lookup, unavailable engine behavior, PT-BR analysis vs normalization separation and deterministic text chunking.
- [ ] **Step 2: Run tests** and confirm imports/functions are absent.
- [ ] **Step 3: Adapt the legacy Piper/Kokoro code** to worker conventions; do not retain legacy API globals, local `file://` helpers or SQLite assumptions.
- [ ] **Step 4: Test missing engine/model/eSpeak/FFmpeg dependencies** and assert normalized capability exceptions rather than raw import/process errors.
- [ ] **Step 5: Run TTS unit tests**; expected PASS without requiring a real model download.
- [ ] **Step 6: Commit** `feat: port Piper and Kokoro worker engines`.

### Task 6: Add durable TTS jobs, preview and PT-BR analysis API

**Files:**
- Create: `speech_worker/tts/runner.py`
- Modify: `speech_worker/worker.py`
- Modify: `src/services/speech_jobs_service.py`
- Modify: `src/api/routes/speech_jobs.py`
- Modify: `src/api/routes/speech.py`
- Test: `src/test_speech_tts_jobs.py`
- Modify/Test: `src/test_speech_api.py`
- Modify/Test: `src/test_speech_worker_bootstrap.py`

**Interfaces:**
- Consumes: Task 5 engine registry; Task 1 common jobs/artifacts.
- Produces: `POST /speech/jobs/tts`, `POST /speech/jobs/tts/preview`, `POST /speech/tts/analyze-text`; worker execution stages `preparing -> chunk -> exporting -> completed`.

- [ ] **Step 1: Write failing API tests** for full TTS and preview job creation, output format/speed/voice/language/preset validation and lightweight PT-BR analysis.
- [ ] **Step 2: Write worker tests** for TTS dispatch, progress persistence, preview text limiting, artifact creation and failure normalization.
- [ ] **Step 3: Run targeted tests** and confirm FAIL.
- [ ] **Step 4: Implement API/service/runner dispatch** using the existing claim/lease system.
- [ ] **Step 5: Add cancellation test during chunk generation** and capability-loss-after-queue test; expected cancelled/failed durable job with no false completed artifact.
- [ ] **Step 6: Run** `python -m pytest -q src/test_speech_tts_jobs.py src/test_speech_api.py src/test_speech_worker_bootstrap.py`; expected PASS.
- [ ] **Step 7: Commit** `feat: add durable TTS jobs and preview`.

### Task 7: Voice registry, samples and PT-BR comparison

**Files:**
- Create: `src/services/speech_assets_service.py`
- Modify: `src/services/speech_capabilities_service.py` if created in Task 8 order; otherwise define DTO ownership here and move implementation in Task 8
- Modify: `src/api/routes/speech.py`
- Modify: `speech_worker/tts/runner.py`
- Test: `src/test_speech_voice_registry.py`
- Test: `src/test_speech_voice_samples.py`
- Test: `src/test_speech_voice_compare.py`

**Interfaces:**
- Consumes: Task 5 normalized voices and Task 6 jobs.
- Produces: voice listing, sample listing/generation/regeneration, all-samples generation and durable voice-comparison jobs with audio + JSON + optional Markdown reports.

- [ ] **Step 1: Write failing voice registry tests** for stable id, display name, engine, locale, availability, source type and sample state.
- [ ] **Step 2: Write failing sample tests** for one/all sample generation and safe managed artifact URLs.
- [ ] **Step 3: Write failing comparison tests** for per-voice success/failure, progress `voice N of M`, JSON report and Markdown report metadata.
- [ ] **Step 4: Implement worker/API/assets behavior** using speech artifacts or managed speech assets, never arbitrary local URLs.
- [ ] **Step 5: Run the three test modules**; expected PASS.
- [ ] **Step 6: Commit** `feat: add speech voice samples and comparison`.

### Task 8: Real worker capabilities and diagnostics

**Files:**
- Create: `speech_worker/runtime/capabilities.py`
- Create: `speech_worker/runtime/diagnostics.py`
- Create: `src/services/speech_capabilities_service.py`
- Modify: `speech_worker/worker.py`
- Modify: `src/api/routes/speech.py`
- Test: `src/test_speech_capabilities.py`
- Test: `src/test_speech_diagnostics.py`

**Interfaces:**
- Consumes: existing `SpeechWorkerState`; Task 5 TTS registry.
- Produces: normalized capability payload containing CPU/CUDA/GPU/VRAM, compute types, FFmpeg, eSpeak, STT/diarization readiness, HF access presence, Piper/Kokoro, voices/models and output formats; diagnostic checks with actionable status/reason.

- [ ] **Step 1: Write failing capability tests** with dependency probes mocked present/absent; ensure no secret value appears in output.
- [ ] **Step 2: Write failing diagnostic tests** for missing HF access, missing FFmpeg, missing eSpeak, CPU-only runtime and unavailable TTS engine.
- [ ] **Step 3: Implement pure probe functions in the worker** and persist normalized capabilities through worker heartbeat/state.
- [ ] **Step 4: Implement lightweight API read models** over persisted worker state, not direct heavy imports.
- [ ] **Step 5: Run** `python -m pytest -q src/test_speech_capabilities.py src/test_speech_diagnostics.py`; expected PASS.
- [ ] **Step 6: Commit** `feat: add Speech runtime capabilities and diagnostics`.

### Task 9: Artifact download, history actions and Biblioteca safety

**Files:**
- Modify: `src/services/speech_assets_service.py`
- Modify: `src/services/speech_result_importer.py`
- Modify: `src/services/speech_jobs_service.py`
- Modify: `src/api/routes/speech_jobs.py`
- Test: `src/test_speech_artifact_api.py`
- Test: `src/test_speech_history.py`
- Modify/Test: `src/test_speech_result_importer.py`

**Interfaces:**
- Consumes: durable artifacts/jobs from Tasks 1, 4, 6 and 7.
- Produces: validated artifact download endpoint, filtered history, retry/duplicate-as-new-job, explicit artifact deletion semantics and Biblioteca linkage/readbacks.

- [ ] **Step 1: Write failing download tests** for valid artifact, missing artifact, path escape/tampered storage key and unsupported access.
- [ ] **Step 2: Write history tests** for newest-first, operation/status filter, error summary, active progress, retry-as-new-job and cancel rules.
- [ ] **Step 3: Write deletion tests** proving job/history cleanup does not silently remove referenced transcript/Biblioteca data and artifact removal requires explicit safe action.
- [ ] **Step 4: Implement service/routes** with storage-root validation and reference checks.
- [ ] **Step 5: Run the three modules**; expected PASS.
- [ ] **Step 6: Commit** `feat: add safe Speech history and artifact access`.

### Task 10: Typed frontend speech client and `/audio` shell

**Files:**
- Create: `frontend/lib/speech-types.ts`
- Create: `frontend/lib/speech-api.ts`
- Create: `frontend/app/audio/page.tsx`
- Create: `frontend/components/audio/audio-workspace.tsx`
- Modify: `frontend/components/layout/sidebar.tsx`
- Test: use existing frontend test convention if present; otherwise verify via TypeScript/build in this task.

**Interfaces:**
- Consumes: Tasks 2–9 API contracts.
- Produces: typed API client and single `/audio` workspace with sections `Visão geral`, `Transcrever`, `Gerar voz`, `Histórico`, `Presets`, `Vozes e modelos`, `Diagnóstico`, `Configurações`.

- [ ] **Step 1: Add typed DTOs/API methods** matching backend response names exactly.
- [ ] **Step 2: Create `/audio` route/workspace** and add one `Áudio` global sidebar item; do not add eight global menu entries.
- [ ] **Step 3: Add loading/error/empty section states** and URL/query-state handling if the current frontend pattern supports it.
- [ ] **Step 4: Run** `cd frontend; npx tsc --noEmit`; expected PASS.
- [ ] **Step 5: Run** `npm run build`; expected PASS and `/audio` included.
- [ ] **Step 6: Commit** `feat: add native Audio workspace shell`.

### Task 11: STT user interface

**Files:**
- Create: `frontend/components/audio/transcription-panel.tsx`
- Create: `frontend/components/audio/transcription-result.tsx`
- Modify: `frontend/components/audio/audio-workspace.tsx`
- Modify: `frontend/lib/speech-api.ts`

**Interfaces:**
- Consumes: Task 3 STT create API; Tasks 4/9 results/artifacts/mappings.
- Produces: browser upload/configuration/result workflow with guided + advanced controls and speaker/artifact actions.

- [ ] **Step 1: Implement upload/select state** with accepted formats and server-error display; do not treat client extension filtering as authoritative validation.
- [ ] **Step 2: Implement guided controls** for preset, language, diarization, speaker counts, quiet speech, initial prompt and output formats.
- [ ] **Step 3: Implement collapsible advanced controls** for model/device/compute/batch/VAD/chunk/offline/diarization model with capability-based disable/warnings.
- [ ] **Step 4: Implement job polling/result view** for progress, segments, timestamps, speakers, mappings, copy text, artifacts and Biblioteca action.
- [ ] **Step 5: Verify frontend TypeScript/build** and manually inspect representative narrow/wide layouts.
- [ ] **Step 6: Commit** `feat: add complete STT Audio workspace`.

### Task 12: TTS, voices and comparison user interface

**Files:**
- Create: `frontend/components/audio/tts-panel.tsx`
- Create: `frontend/components/audio/voices-models-panel.tsx`
- Modify: `frontend/components/audio/audio-workspace.tsx`
- Modify: `frontend/lib/speech-api.ts`

**Interfaces:**
- Consumes: Tasks 6–8 APIs.
- Produces: text analysis, normalization toggle, engine/voice selection, speed/format, preview/full generation, samples, model/voice availability and PT-BR comparison UI.

- [ ] **Step 1: Implement TTS editor and controls** with original text preserved and advisory PT-BR analysis separate from normalization.
- [ ] **Step 2: Implement preview/full job polling and browser audio playback/download** through managed artifact endpoints.
- [ ] **Step 3: Implement voices/models view** with engine/locale/status filters, missing-runtime reasons and sample actions.
- [ ] **Step 4: Implement PT-BR comparison flow** with per-voice status and report artifacts.
- [ ] **Step 5: Verify TypeScript/build and unavailable-engine UI behavior** using mocked/offline backend states where practical.
- [ ] **Step 6: Commit** `feat: add complete TTS and voice workspace`.

### Task 13: History, presets, diagnostics, settings and overview UI

**Files:**
- Create: `frontend/components/audio/audio-overview.tsx`
- Create: `frontend/components/audio/history-panel.tsx`
- Create: `frontend/components/audio/presets-panel.tsx`
- Create: `frontend/components/audio/diagnostics-panel.tsx`
- Create: `frontend/components/audio/settings-panel.tsx`
- Modify: `frontend/components/audio/audio-workspace.tsx`
- Modify: `frontend/lib/speech-api.ts`

**Interfaces:**
- Consumes: Tasks 2, 8 and 9 APIs.
- Produces: operational dashboard, durable job history, preset CRUD, real diagnostics and non-secret settings UI.

- [ ] **Step 1: Implement overview** using real worker/queue/capability data and actionable warnings.
- [ ] **Step 2: Implement history filters/actions** with explicit confirmation for destructive artifact actions.
- [ ] **Step 3: Implement preset CRUD/duplicate/save-current** while disabling mutation of built-ins.
- [ ] **Step 4: Implement diagnostics** showing actual check status/details rather than mock terminal output.
- [ ] **Step 5: Implement settings** with secret-presence indicators and no secret echo.
- [ ] **Step 6: Run frontend TypeScript/build**; expected PASS.
- [ ] **Step 7: Commit** `feat: complete Speech Suite management UI`.

### Task 14: Runtime packaging, docs and smoke verification

**Files:**
- Create: `scripts/speech_stt_smoke.py`
- Create: `scripts/speech_tts_smoke.py`
- Modify: `requirements.txt` only for lightweight shared requirements actually needed by the API
- Create/Modify: worker-specific requirements/install documentation as required by current project conventions
- Modify: `README.md`
- Modify: `.github/workflows/case-radar-ci.yml`
- Create: `docs/superpowers/specs/2026-09-28-unified-speech-parity-matrix.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: reproducible local setup, non-heavy CI regression, opt-in real runtime smoke commands and a final old-to-new parity matrix.

- [ ] **Step 1: Add a parity matrix** mapping every useful legacy Speech Studio backend/UI capability to migrated/replaced/excluded-with-reason status.
- [ ] **Step 2: Add STT smoke script** that creates a real small STT job, executes/observes worker completion, validates transcript/artifacts and exits nonzero on failure.
- [ ] **Step 3: Add TTS smoke script** supporting `--engine kokoro|piper`, preview/full generation and artifact validation; unavailable optional engine must report SKIP/unavailable distinctly from regression failure.
- [ ] **Step 4: Update README** with Python 3.11 worker setup, FFmpeg, CUDA/CPU, HF diarization requirements, Piper/Kokoro/eSpeak requirements, worker start command and both smoke commands.
- [ ] **Step 5: Extend CI regression** with all non-heavy speech unit/API tests, migration smoke and frontend TypeScript/build; do not require model downloads or GPU in standard CI.
- [ ] **Step 6: Run full backend suite** `python -m pytest -q`; expected PASS.
- [ ] **Step 7: Run frontend** `npx tsc --noEmit` and `npm run build`; expected PASS.
- [ ] **Step 8: Run migration smoke** upgrade/downgrade boundary for new migration on disposable PostgreSQL; expected PASS.
- [ ] **Step 9: Run real local runtime acceptance**: STT smoke, Kokoro TTS smoke, Piper TTS smoke where installed, artifact download, Biblioteca import/link and diagnostics/capabilities inspection. Record unavailable optional engine as environment limitation, not false PASS.
- [ ] **Step 10: Commit** `test: verify complete Speech Studio parity`.

### Task 15: Whole-branch parity review and integration

**Files:**
- Review all changed files against the spec and parity matrix.

**Interfaces:**
- Consumes: Tasks 1–14.
- Produces: one review-ready branch whose user-visible Speech Suite no longer depends on old Speech Studio runtime.

- [ ] **Step 1: Re-read** `docs/superpowers/specs/2026-09-28-unified-speech-suite-parity-design.md` and the final parity matrix; confirm every success criterion has concrete evidence.
- [ ] **Step 2: Run the documented Speech regression suite and full backend suite** from a clean environment.
- [ ] **Step 3: Run frontend TypeScript/build** from clean dependencies as CI does.
- [ ] **Step 4: Inspect for accidental heavy imports in main API** and for unrestricted filesystem paths/secrets in browser responses.
- [ ] **Step 5: Review failure paths** for missing HF access, CPU-only system, missing FFmpeg/eSpeak, unavailable Kokoro/Piper, cancellation and stale worker lease.
- [ ] **Step 6: Open PR to `master`, wait for fresh CI on the exact head SHA, address review findings, then squash-merge only when green.**
- [ ] **Step 7: Verify fresh CI on the resulting `master` commit and delete the short-lived feature branch.**

## Self-review result

- **Spec coverage:** all product areas in the approved design are assigned to Tasks 1–14; Task 15 owns whole-branch acceptance/integration.
- **Step scan:** tasks use explicit files, interfaces, verification commands and expected outcomes; no implementation body is prewritten where tests/signatures determine it.
- **Type consistency:** all heavy operations converge on `speech_jobs`; STT/TTS presets share `speech_presets`; browser artifacts flow through managed artifact endpoints; worker capabilities flow through `SpeechWorkerState`.
- **Review Focus coverage:** invalid uploads (Task 3), capability drift and cancellation (Task 6), missing runtime dependencies (Tasks 5/8/12), referenced-data deletion safety (Task 9).
- **Proportion:** the plan decomposes the approved large subsystem into reviewable tasks without duplicating the implementation code itself.
