# Unified Speech Suite — Complete Speech Studio Parity Design

Date: 2026-09-28
Status: approved design, pending implementation plan
Supersedes for completion scope: `docs/superpowers/specs/2026-09-05-unified-speech-suite-design.md`

## 1. Goal

Complete the Speech Suite inside Content Radar so the old Speech Studio and Speech Studio frontend are no longer needed for day-to-day use.

The target is **functional parity with the useful capabilities of Speech Studio**, migrated into Content Radar's architecture rather than embedded as a second application.

After completion, the user should be able to do all normal speech work from Content Radar:

- local speech-to-text (STT);
- WhisperX alignment;
- diarization and speaker mapping;
- advanced VAD controls;
- guided and advanced STT presets;
- TXT/JSON/SRT/VTT exports;
- text-to-speech (TTS);
- Piper and Kokoro engines;
- PT-BR text analysis and normalization;
- TTS preview and full generation;
- voice browsing and voice samples;
- PT-BR voice comparison;
- history and job inspection;
- personal presets;
- model/engine/voice capability inspection;
- local environment diagnostics;
- speech settings;
- integration with Content Radar Biblioteca;
- safe artifact download and retention.

The old Speech Studio repositories remain reference implementations until parity is verified. They are not runtime dependencies.

## 2. Product success criteria

The Speech Suite is complete only when all of the following are true:

1. `/audio` exists and is the single Content Radar entry point for speech workflows.
2. STT works end-to-end from browser upload to normalized transcript and artifacts.
3. TTS works end-to-end through both supported engines where installed.
4. History is persistent in PostgreSQL and covers STT and TTS.
5. Presets are native Content Radar data, not copied static UI only.
6. Voice/model capability data reflects the real local worker environment.
7. Diagnostics report the real local speech environment, not mock values.
8. Speaker mapping works without rewriting raw diarization labels.
9. Generated artifacts are downloadable through validated API endpoints.
10. Biblioteca can consume completed STT results without a separate Speech Studio workflow.
11. Worker failure, cancellation, stale lease recovery, capability loss and missing optional dependencies degrade cleanly.
12. A parity matrix shows every useful old Speech Studio function as migrated, replaced by an equivalent, or intentionally excluded with a documented reason.
13. No useful workflow requires launching the old Speech Studio frontend or API.

A green frontend build alone is not completion. A green backend test suite alone is not completion. Runtime smoke tests for STT and TTS are part of the acceptance criteria.

## 3. Source-of-truth repositories

### 3.1 Current product

`Gabriel0liv/Content-Radar`

Primary branch: `master`.

Existing speech foundation already includes:

- PostgreSQL-backed `speech_jobs`;
- `operation` supporting `stt` and `tts` at schema level;
- `speech_presets`;
- `speech_artifacts`;
- `speech_speaker_mappings`;
- worker state/capabilities;
- STT job creation/upload;
- job listing/get/cancel;
- speech worker heartbeat/status;
- STT execution and result import foundation;
- storage and artifact concepts.

This existing foundation is extended rather than replaced.

### 3.2 Legacy behavior reference

`Gabriel0liv/Speech-Studio`

Useful backend/runtime areas include:

- `transcribe.py`;
- `synthesize.py`;
- `api/routes_stt.py`;
- `api/routes_tts.py`;
- `api/routes_voices.py`;
- `api/routes_history.py`;
- `api/routes_presets.py`;
- job/progress utilities;
- health/runtime checks;
- `src/tts/base.py`;
- `src/tts/registry.py`;
- `src/tts/piper_engine.py`;
- `src/tts/kokoro_engine.py`;
- `src/tts/ptbr_text.py`;
- `src/tts/text_chunking.py`;
- preset and speaker-profile definitions;
- artifact/export behavior.

### 3.3 Legacy UI reference

`Gabriel0liv/Speech-Studio-frontend`

Useful product surfaces include:

- Dashboard;
- Transcrição;
- Texto para Voz;
- Histórico;
- Presets;
- Modelos;
- Diagnóstico;
- Configurações.

The old UI is a behavior/reference source, not a component library to embed.

## 4. Architectural decision

Use **native migration into Content Radar**, not iframe, proxy, remote Speech Studio API, or a second frontend.

The target remains:

```text
Browser
  |
  v
Content Radar Next.js
  |
  v
Content Radar FastAPI
  |             |
  |             +---- PostgreSQL
  |
  +---- speech_jobs
            |
            v
      speech_worker
        |      |
        |      +---- Piper / Kokoro
        +----------- WhisperX / pyannote / FFmpeg / Torch
```

The main backend owns durable product state. The speech worker owns heavy local execution.

### 4.1 What stays in the main API

- validation;
- persistence;
- presets;
- settings metadata;
- safe upload staging;
- safe artifact download;
- job lifecycle orchestration;
- transcript import;
- speaker mapping;
- capability/status read models;
- user-facing error normalization.

### 4.2 What stays in the worker

- model loading;
- FFmpeg conversion;
- STT inference;
- alignment;
- diarization;
- TTS inference;
- text chunk generation execution;
- audio merging/conversion;
- hardware/runtime discovery;
- model/engine/voice discovery;
- heavy-job progress reporting.

The main API must not import Torch, WhisperX, pyannote or heavy TTS libraries.

## 5. `/audio` information architecture

Add one top-level sidebar item:

```text
Áudio -> /audio
```

The page is a single Speech Suite workspace with internal tabs/sections:

```text
/audio
├── Visão geral
├── Transcrever
├── Gerar voz
├── Histórico
├── Presets
├── Vozes e modelos
├── Diagnóstico
└── Configurações
```

Do not add eight new items to the global sidebar.

The page should follow the visual language already used by Content Radar: dark application shell, consistent spacing, typography, forms, cards, status chips, loading states and responsive layouts.

The old Speech Studio visual design may inform useful interaction patterns, but the new implementation must look native to Content Radar.

## 6. Overview

The overview is an operational dashboard, not a marketing page.

Show:

- worker online/offline;
- current active job;
- queued jobs;
- recent completed/failed jobs;
- CUDA/CPU status;
- diarization readiness;
- TTS engines available;
- counts of installed/discovered voices;
- shortcuts to Transcrever and Gerar voz;
- warnings requiring action, such as missing HF token or unavailable engine.

The overview must be based on real API data.

## 7. STT — transcription

### 7.1 Input

Support browser upload for common audio/video formats, including at minimum the formats already used by Speech Studio:

- MP3;
- WAV;
- MP4;
- MKV;
- MOV;
- M4A;
- WEBM.

Validation must occur server-side. File names are never trusted as storage paths.

### 7.2 User-facing presets

Keep built-ins:

- `fast` / Rápido;
- `balanced` / Equilibrado;
- `maximum_quality` / Máxima qualidade.

Allow personal STT presets.

The UI must show the resolved technical configuration so presets remain inspectable.

### 7.3 Guided STT controls

Expose simple controls first:

- preset;
- language: automatic / PT / EN / ES / explicit code;
- identify speakers;
- exact speaker count or min/max range;
- quiet/sensitive speech mode;
- initial vocabulary/context prompt;
- output formats.

### 7.4 Advanced STT controls

Expose advanced controls in a collapsible section:

- model;
- device: auto/cuda/cpu;
- compute type;
- batch size;
- diarization model;
- VAD onset;
- VAD offset;
- chunk size;
- exact/min/max speakers;
- initial prompt;
- offline mode;
- cache/model behavior where supported;
- export formats.

Unsafe combinations should display a warning before submission. The worker remains authoritative for final capability resolution.

### 7.5 STT execution flow

```text
UI upload
→ POST /speech/jobs/stt/upload
→ stage managed input
→ create speech_jobs row
→ worker claims job
→ FFmpeg normalize/extract
→ WhisperX/faster-whisper inference
→ alignment
→ optional diarization
→ normalize result
→ create artifacts
→ import transcript/version
→ optional Biblioteca link
→ mark completed
```

### 7.6 STT result view

Show:

- status;
- current stage;
- progress;
- duration;
- detected language;
- model/device/compute configuration;
- transcript segments;
- timestamps;
- detected speakers;
- display-name mapping;
- artifacts;
- copy plain text;
- TXT/JSON/SRT/VTT download;
- save/import to Biblioteca when applicable;
- collapsed debug/error details.

### 7.7 Speaker mapping

Raw labels remain immutable:

```text
SPEAKER_00
SPEAKER_01
```

Display names are stored separately:

```text
SPEAKER_00 -> Gabriel
SPEAKER_01 -> João
```

Mapping changes must affect rendering and exports generated from normalized transcript data without destroying engine metadata.

### 7.8 Subtitle behavior

Preserve professional formatting behavior from Speech Studio where applicable:

- speaker-aware splitting;
- at most two visual lines per subtitle block;
- readable line-length targets;
- minimum/maximum subtitle duration;
- speaker-change boundaries;
- silence-aware boundaries;
- correct SRT/VTT timestamp formatting.

Normalized transcript data is canonical; subtitle files are derived artifacts.

## 8. TTS — text to speech

### 8.1 Engines

Migrate engine abstraction and support for:

- Kokoro;
- Piper.

Do not execute TTS directly inside the FastAPI process.

Target worker structure:

```text
speech_worker/tts/
├── __init__.py
├── base.py
├── registry.py
├── piper_engine.py
├── kokoro_engine.py
├── ptbr_text.py
└── text_chunking.py
```

The old Speech Studio files are adapted to worker/storage/job conventions rather than blindly copied.

### 8.2 TTS request

A TTS job includes:

- text;
- engine;
- voice;
- output format;
- speed;
- language;
- PT-BR normalization option;
- PT-BR analysis option;
- optional preset;
- preview/full mode;
- preview character limit when previewing;
- engine-specific advanced options where needed.

### 8.3 TTS endpoints

Public browser-facing behavior should be represented through Content Radar endpoints such as:

```text
POST /speech/jobs/tts
POST /speech/jobs/tts/preview
POST /speech/tts/analyze-text
POST /speech/tts/compare-voices
```

Exact route factoring may be refined in the implementation plan, but all durable heavy work must use the common job system.

Text analysis may execute synchronously if it remains lightweight and does not import a heavy TTS engine.

### 8.4 TTS execution flow

```text
UI text/config
→ API validates engine-neutral request
→ speech_jobs row operation=tts
→ worker claims job
→ resolve engine/voice
→ optional PT-BR normalization
→ text chunking
→ synthesize chunks
→ merge/convert
→ persist artifact metadata
→ mark completed
→ UI previews/downloads result
```

### 8.5 TTS progress

Retain meaningful stages equivalent to Speech Studio:

- preparing;
- chunk generation;
- exporting/merging;
- completed.

For voice comparison:

- preparing;
- voice N of M;
- report generation;
- completed.

Progress must be stored in `speech_jobs`, not only streamed to one HTTP request.

### 8.6 PT-BR text analysis and normalization

Migrate the useful behavior from `ptbr_text.py`.

The UI should support:

- analyze text before generation;
- show pronunciation/orthography suggestions;
- normalize abbreviations/numbers/known patterns when enabled;
- retain the original user text as request metadata;
- show what normalization is enabled.

Analysis suggestions are advisory. The system must not silently rewrite user text unless normalization is enabled.

### 8.7 Preview

Preview generation uses the same engine path as full generation but limits text/chunks.

A preview is still represented as a job/artifact so history and failures remain observable.

### 8.8 Output formats

Support at minimum:

- WAV;
- MP3 where the runtime has the required conversion path.

The capability response must describe output formats actually available.

## 9. Voice management

### 9.1 Voice registry

Expose a normalized voice view independent of engine implementation.

Voice metadata includes where available:

- stable voice id/alias;
- display name;
- engine;
- language;
- locale;
- style/description;
- availability;
- source type: built-in/discovered/local;
- model asset status;
- sample availability;
- engine-specific metadata.

### 9.2 Voice samples

Preserve Speech Studio's useful sample workflow.

Support:

- list existing samples;
- generate one sample;
- generate samples for all supported voices;
- play sample in browser;
- regenerate sample;
- report sample-generation failure.

Samples become `speech_artifacts` or managed speech assets. Browser responses never expose unrestricted arbitrary filesystem URLs.

### 9.3 PT-BR voice comparison

Preserve the ability to compare multiple Portuguese voices.

A comparison run produces:

- per-voice audio artifacts;
- structured JSON report;
- Markdown report if still useful;
- per-voice success/failure;
- duration/runtime metadata where available.

The comparison is a worker job because it is heavy and potentially long-running.

## 10. Models and engine capabilities

The old Speech Studio had a dedicated Models page. The unified product combines models and voices into `Vozes e modelos`.

Expose real capabilities such as:

- STT engines installed;
- Whisper models known/available;
- CUDA availability;
- GPU name;
- approximate VRAM if detectable;
- supported compute types;
- diarization readiness;
- configured diarization model;
- HF token/access state without returning the token;
- Kokoro availability;
- Piper availability;
- installed/discovered voices;
- supported output formats;
- FFmpeg availability;
- eSpeak NG availability where required by the selected TTS path.

Capability discovery belongs to the worker. The API returns the worker's normalized capability state.

The UI hides or disables unavailable options and explains why.

## 11. History

Use Content Radar `speech_jobs` as the durable history for STT and TTS.

History supports:

- newest-first listing;
- operation filter;
- status filter;
- STT/TTS identification;
- input/source display;
- text snippet for TTS;
- created/started/finished timestamps;
- progress for active jobs;
- resolved configuration inspection;
- artifact access;
- transcript link;
- error summary;
- cancellation of cancellable jobs;
- retry/duplicate-as-new-job where safe and useful.

Do not migrate the old SQLite history database as a second source of truth.

Deleting history must have explicit semantics. Do not silently delete referenced transcripts or artifacts.

Recommended behavior:

- normal UI: hide/archive or delete eligible job records only when safe;
- artifact deletion: explicit separate action with reference checks;
- no global destructive `clear all and files` operation without a clear confirmation flow.

## 12. Presets

Use `speech_presets` for both STT and TTS.

### 12.1 Built-ins

Built-ins are code/seed-controlled and immutable through normal delete actions.

STT built-ins:

- Rápido;
- Equilibrado;
- Máxima qualidade.

TTS built-ins may be seeded from useful Speech Studio presets after audit, but only presets that represent meaningful engine-neutral user intent should become global built-ins.

### 12.2 Personal presets

Allow:

- create;
- duplicate;
- rename;
- edit;
- delete;
- save current configuration as preset;
- apply preset;
- inspect resolved configuration.

A preset stores the full supported configuration JSON for its operation.

## 13. Speaker profiles

Speech Studio had speaker-profile concepts separate from generic presets.

For parity, retain useful speaker-profile behavior if it affects diarization configuration or export naming.

Do not infer real-world identity automatically.

Initial scope:

- reusable profile names/configuration only where they provide actual technical behavior;
- transcript/job speaker display mapping remains separate;
- no biometric speaker identification.

If the old speaker profiles are only UI labels around diarization counts/settings, migrate them as STT presets instead of creating a redundant model.

## 14. Diagnostics

`/audio` includes a real Diagnostics section.

Diagnostics should inspect and report at minimum:

- Python runtime used by the worker;
- worker process online state;
- PostgreSQL job queue accessibility;
- writable speech storage;
- FFmpeg;
- CUDA;
- GPU name;
- VRAM where detectable;
- PyTorch;
- WhisperX;
- faster-whisper/CTranslate2;
- pyannote;
- HF token configured state;
- diarization model access/readiness;
- Kokoro;
- Piper;
- eSpeak NG when applicable;
- model/cache directories;
- available voices;
- output conversion capability.

Each check returns a structured status:

```text
ok
warning
error
unavailable
```

Diagnostics should include actionable messages, not only raw tracebacks.

Do not report the old SQLite history database because Content Radar uses PostgreSQL.

## 15. Settings

The Settings section controls persistent/default speech behavior without exposing secrets.

Settings candidates:

- default STT preset;
- default language;
- default diarization preference;
- default TTS engine;
- default voice;
- default output format;
- default PT-BR normalization;
- default export formats;
- offline/cache preference;
- artifact retention policy;
- input retention policy;
- debug artifact retention;
- hardware override policy where appropriate;
- model/cache paths if safe and necessary.

Secrets such as HF tokens should be represented as configured/not configured and continue to come from environment/secret storage unless a dedicated secret-storage mechanism is introduced later.

Do not store raw secret values in `speech_presets` or return them from normal API responses.

## 16. Data model

### 16.1 Existing tables retained

#### `speech_jobs`

Durable STT/TTS queue and history.

Important fields already present:

- operation;
- status;
- stage;
- progress;
- requested config;
- resolved config;
- input path;
- reference source;
- transcript;
- worker/lease fields;
- result JSON;
- normalized error fields;
- timestamps.

TTS support already exists at the schema constraint level and should be implemented through the same table.

#### `speech_presets`

Native STT/TTS presets.

#### `speech_artifacts`

Generated/downloadable artifacts tied to jobs.

#### `speech_speaker_mappings`

Raw speaker to display-name mapping.

#### `speech_worker_state`

Heartbeat and capabilities.

### 16.2 Possible schema additions

Only add a table if audit shows persistent data cannot fit cleanly into existing models.

Likely candidates:

- `speech_settings` for persisted user/application defaults;
- `speech_voice_presets` only if user-created voice configuration cannot cleanly use `speech_presets`.

Do not create a voice table merely to mirror engine-discovered static voices. Runtime discovery belongs in worker capabilities unless persistence is needed.

Every schema change must use a new Alembic migration. Never modify an applied migration.

## 17. Artifact and storage design

Use managed speech storage rooted at `SPEECH_DATA_ROOT`.

Target structure:

```text
data/speech/
├── inputs/
├── jobs/
├── artifacts/
├── samples/
├── comparisons/
├── cache-or-links/
└── voices/
```

Rules:

- use server-generated storage keys;
- sanitize user filenames;
- prevent path traversal;
- temporary normalized WAV files are removed after completion unless debug retention is enabled;
- original uploads follow explicit retention rules;
- generated artifacts survive while referenced according to retention policy;
- downloads go through validated API endpoints;
- do not expose arbitrary local file URLs;
- artifact metadata is durable even when a file later becomes unavailable, so the UI can report the missing artifact cleanly.

## 18. Job protocol and concurrency

Continue using PostgreSQL job claiming.

Worker behavior:

1. heartbeat capabilities;
2. recover eligible expired leases;
3. claim next compatible queued job with row locking;
4. mark running;
5. heartbeat/extend lease;
6. update stage/progress;
7. observe cancellation requests between expensive stages/chunks;
8. write structured result/artifacts;
9. complete or fail with normalized error;
10. release heavy resources before the next job.

Initial heavy concurrency remains one heavy job at a time per worker unless capability-based parallelism is deliberately added later.

Do not restore the old Speech Studio process-local heavy-job lock as the product-wide coordination mechanism. PostgreSQL job ownership is authoritative.

## 19. Cancellation

Cancellation rules:

- queued job: cancel immediately;
- running job: set cancellation request and stop at the nearest safe checkpoint;
- completed/failed/cancelled: idempotent no-op or clear conflict response;
- partial temporary files are cleaned according to retention/debug policy;
- cancellation does not produce a successful transcript/TTS artifact accidentally.

Long TTS multi-chunk and multi-voice comparison loops must check cancellation between chunks/voices.

## 20. Failure handling

Normalize failures into stable user-facing codes.

Examples:

- `speech_worker_offline`;
- `ffmpeg_missing`;
- `input_invalid`;
- `cuda_unavailable`;
- `out_of_memory`;
- `stt_engine_unavailable`;
- `diarization_unavailable`;
- `hf_token_missing`;
- `hf_model_access_denied`;
- `tts_engine_unavailable`;
- `voice_unavailable`;
- `artifact_write_failed`;
- `cancelled`;
- `speech_worker_error`.

Raw debug information may be retained in debug logs, but normal UI errors should explain what the user can do next.

A failed database flush/transaction must rollback before recovery actions, following the same robustness principle already applied to the Case Radar worker.

## 21. Hardware-aware behavior

The worker reports what is really available.

Preset resolution may adapt to capabilities, for example:

- CUDA unavailable -> CPU-safe STT configuration;
- low VRAM -> smaller batch / int8 / medium fallback;
- diarization unavailable -> STT remains usable without speaker separation;
- Piper missing -> Kokoro remains usable if available;
- Kokoro missing -> Piper remains usable if available;
- FFmpeg missing -> workflows requiring conversion are blocked with a clear diagnostic.

Do not silently change a user-selected advanced setting without showing the resolved configuration.

## 22. Biblioteca integration

Speech remains a native Content Radar capability.

For an existing reference source:

```text
reference
→ speech job
→ transcript result
→ transcript version
→ active transcript policy
→ search/topic enrichment
```

For manually uploaded media:

- allow transcription without creating a Biblioteca record;
- after completion allow promotion/linking to Biblioteca where supported;
- avoid duplicating the same artifact unnecessarily.

YouTube reference transcription choices should conceptually remain:

- Automático;
- Legenda do YouTube;
- Local rápido;
- Local equilibrado;
- Local máxima qualidade.

Automatic mode should prefer existing/cheap captions before expensive local inference unless user settings override that policy.

## 23. API surface

Target public Content Radar speech API, subject to implementation-plan naming refinement:

```text
GET    /speech/status
GET    /speech/capabilities
GET    /speech/diagnostics

GET    /speech/jobs
GET    /speech/jobs/{id}
POST   /speech/jobs/{id}/cancel
POST   /speech/jobs/{id}/retry

POST   /speech/jobs/stt/upload
POST   /speech/jobs/tts
POST   /speech/jobs/tts/preview

POST   /speech/tts/analyze-text
POST   /speech/tts/compare-voices

GET    /speech/presets
POST   /speech/presets
PATCH  /speech/presets/{id}
DELETE /speech/presets/{id}

GET    /speech/voices
GET    /speech/voices/samples
POST   /speech/voices/{voice_id}/sample
POST   /speech/voices/samples/generate

GET    /speech/jobs/{id}/artifacts
GET    /speech/artifacts/{id}/download

GET    /speech/settings
PATCH  /speech/settings

PATCH  /transcripts/{id}/speakers/{raw_speaker}
```

Do not expose worker-internal endpoints to the browser.

## 24. Frontend behavior

### 24.1 Data layer

Create a focused speech API client/hooks layer rather than putting `fetch` calls throughout components.

The UI should handle:

- polling active jobs;
- stopping polling on terminal status;
- worker offline states;
- optimistic-but-safe preset edits where appropriate;
- artifact download;
- cancellation;
- form validation;
- capability-dependent controls.

### 24.2 Transcription page

Two-column layout on desktop:

- main: upload, file summary, job progress/result/transcript;
- side: guided configuration, with advanced collapsible options.

Responsive layout stacks on smaller screens.

### 24.3 TTS page

Two-column layout on desktop:

- main: script text, PT-BR analysis, preview/full result, comparison results;
- side: engine, voice, format, speed, preset and normalization controls.

Voice sample playback should use browser-native audio controls or a simple custom player backed by real artifact URLs.

### 24.4 History

Use a compact table/list with status, type, input/name, created time, duration where available, configuration summary and actions.

### 24.5 Diagnostics

Show structured cards plus optional expanded technical log/details. No fake terminal animation or mock values in production.

## 25. Legacy feature parity matrix

The implementation plan must maintain a live parity checklist at minimum covering:

| Legacy capability | Target in Content Radar | Required outcome |
|---|---|---|
| STT upload | `/audio` Transcrever | Native |
| WhisperX transcription | `speech_worker/stt` | Native |
| Word/segment alignment | normalized transcript | Native |
| pyannote diarization | STT worker | Native |
| exact/min/max speakers | STT config | Native |
| speaker mapping | transcript mappings | Native |
| VAD onset/offset | advanced STT | Native |
| quiet speech mode | guided STT | Native |
| initial prompt | STT config | Native |
| model/device/compute/batch | advanced STT | Native |
| TXT export | artifact endpoint | Native |
| JSON export | artifact endpoint | Native |
| SRT export | artifact endpoint | Native |
| VTT export | artifact endpoint | Native |
| TTS Kokoro | `speech_worker/tts` | Native |
| TTS Piper | `speech_worker/tts` | Native |
| speed | TTS config | Native |
| WAV output | TTS artifact | Native |
| MP3 output | TTS artifact when available | Native |
| preview generation | TTS preview job | Native |
| PT-BR analysis | lightweight API/service | Native |
| PT-BR normalization | TTS worker | Native |
| text chunking | TTS worker | Native |
| voice listing | capabilities/voices API | Native |
| voice samples | speech artifacts | Native |
| generate all samples | worker job | Native |
| PT-BR voice comparison | worker comparison job | Native |
| comparison JSON/MD reports | artifacts | Native |
| jobs/progress | `speech_jobs` | Replaced by stronger native queue |
| process-local heavy lock | PostgreSQL worker claim | Intentionally replaced |
| old SQLite history | PostgreSQL history | Intentionally replaced |
| history list | `/audio` Histórico | Native |
| history file links | artifact downloads | Intentionally safer replacement |
| presets | `speech_presets` | Native |
| speaker profiles | STT preset/profile mapping after audit | Native/equivalent |
| models page | Vozes e modelos | Native |
| diagnostics page | Diagnóstico | Native |
| settings page | Configurações | Native |
| old Dashboard | Visão geral | Native/equivalent |
| standalone frontend | `/audio` | Removed after parity |
| standalone API | Content Radar API | Removed after parity |

The matrix is not complete merely because the rows exist. Each row needs test/evidence during implementation.

## 26. Testing strategy

### 26.1 Unit tests

Cover:

- STT preset resolution;
- TTS request resolution;
- PT-BR text analysis/normalization;
- text chunking;
- engine registry normalization;
- voice capability normalization;
- artifact path safety;
- subtitle formatting;
- speaker mapping;
- settings validation;
- error normalization;
- job retry/cancel state rules.

### 26.2 Repository/service tests

Cover:

- TTS job creation;
- STT/TTS history listing;
- preset CRUD;
- artifact registration;
- speaker mapping persistence;
- settings persistence if added;
- stale worker recovery;
- cancellation transitions;
- worker capability heartbeat.

### 26.3 API tests

Cover the public routes with heavy execution mocked at the worker boundary.

Verify:

- validation;
- status codes;
- no arbitrary local path exposure;
- no secret exposure;
- terminal job responses;
- artifact downloads;
- capability-dependent failures.

### 26.4 Worker tests

Use fake/lightweight engines for protocol tests and engine-specific unit tests where possible.

Cover:

- progress updates;
- cancellation checkpoints;
- temp-file cleanup;
- result normalization;
- TTS chunk merge path;
- per-voice comparison partial failure;
- missing optional dependency behavior.

### 26.5 Frontend tests

At minimum verify:

- `/audio` renders;
- all internal sections are reachable;
- forms produce correct payloads;
- capability-disabled controls behave correctly;
- active job polling stops on completion/failure/cancel;
- artifact links use API URLs;
- diagnostics render warning/error states;
- TTS preview/full actions remain distinct;
- preset create/edit/delete flows.

### 26.6 Runtime smoke tests

A complete implementation requires local runtime evidence beyond mocked CI:

STT smoke:

```text
small audio fixture
→ queue
→ worker
→ completed transcript
→ expected text structure
→ artifacts downloadable
```

TTS smoke for each installed engine:

```text
short PT-BR text
→ queue
→ worker
→ valid audio artifact
→ browser/API download
```

Diarization smoke is conditional on HF access/model availability and should report a meaningful skip/unavailable state rather than failing unrelated STT validation.

GPU-specific smoke is conditional on hardware availability.

## 27. CI strategy

Regular CI must remain runnable without GPU, large model downloads or secret tokens.

CI should therefore:

- run backend unit/integration tests with fake/lightweight worker engines;
- run migration smoke;
- run frontend TypeScript/build;
- validate worker protocol without downloading large models;
- validate TTS registry behavior under missing optional dependencies;
- validate STT behavior under missing diarization credentials;
- keep real provider/speech heavy runtime checks separate/informational where environment support is optional.

Do not make CI depend on CUDA or Hugging Face secrets.

## 28. Dependency strategy

Keep heavy speech dependencies separated from the normal backend.

Target dependency groups remain conceptually:

```text
speech_requirements/
├── base.txt
├── stt-cpu.txt
├── stt-cuda.txt
└── tts.txt
```

If implementation shows that Kokoro and Piper need materially different dependency groups, split them further without moving them into the regular backend requirements.

Installation documentation must cover:

- CPU STT;
- CUDA STT;
- diarization/HF requirements;
- TTS engines;
- FFmpeg;
- eSpeak NG when required;
- how to run the speech worker.

## 29. Security and privacy

- speech processing remains local unless an explicitly configured model download/authentication call is required;
- no arbitrary filesystem path API;
- uploaded names are sanitized;
- download endpoints validate artifact ownership/existence;
- secrets are never returned to the frontend;
- debug logs should redact likely tokens/secrets;
- raw model errors are not blindly persisted as user-facing errors;
- no automatic biometric speaker identity inference.

## 30. Migration and compatibility

Do not migrate the old Speech Studio SQLite database/history as authoritative data.

Do not depend on the old Speech Studio API or frontend during normal operation.

Useful code is migrated/refactored into Content Radar modules.

Until parity is verified:

- old repositories remain available as behavior references;
- parity comparisons can be made against old CLI/API output;
- no destructive archival action is automated.

After parity is verified, archiving the old repositories is a manual user decision outside this implementation scope.

## 31. Implementation boundaries

This project includes completing the Speech Suite. It does not include:

- a full audio editor/DAW;
- waveform editing/cutting timeline;
- voice cloning from arbitrary samples;
- biometric speaker identification;
- cloud TTS vendors unless separately requested;
- distributed multi-node GPU scheduling;
- Redis/Celery unless PostgreSQL job transport proves insufficient;
- automatic deletion/archive of the old Speech Studio repositories.

## 32. Delivery workflow

Follow the repository branch policy:

```text
master
→ short-lived feature branch
→ implementation + tests
→ PR
→ squash merge to master
→ verify master
→ delete stale branch
```

The implementation may be divided into sequential short-lived branches by independently verifiable capability, but no long-lived integration branch should accumulate indefinitely.

Recommended capability sequence for the implementation plan:

1. complete API/domain foundation and speech settings/capability contracts;
2. migrate TTS worker core;
3. complete TTS job protocol/artifacts;
4. complete presets/voices/samples/comparison;
5. complete STT advanced parity and exports/speaker mapping;
6. implement `/audio` shell and overview;
7. implement Transcrever;
8. implement Gerar voz;
9. implement Histórico/Presets/Vozes e modelos;
10. implement Diagnóstico/Configurações;
11. Biblioteca integration parity;
12. complete parity audit and runtime smokes;
13. documentation and final cleanup.

Each branch must start from current `master` after the previous branch is merged.

## 33. Definition of done

The Unified Speech Suite is done when:

- all required migrations are applied cleanly from a fresh database and an upgraded existing database;
- backend tests pass;
- speech regression tests pass;
- frontend TypeScript and production build pass;
- worker protocol tests pass;
- STT runtime smoke succeeds in a supported local configuration;
- TTS runtime smoke succeeds for each installed supported engine;
- `/audio` works without mock data;
- diagnostics reflect actual worker capabilities;
- artifact downloads are functional and safe;
- Biblioteca integration works;
- the parity matrix has no undocumented gaps;
- old Speech Studio is not required for any useful migrated workflow;
- the feature branches have been merged to `master` and cleaned up.
