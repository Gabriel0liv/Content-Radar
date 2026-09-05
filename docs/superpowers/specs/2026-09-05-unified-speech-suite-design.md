# Unified Speech Suite Design

Date: 2026-09-05
Status: proposed for final review
Supersedes: `docs/superpowers/specs/2026-09-05-speech-studio-integration-design.md`

## 1. Goal

Make Content Radar the single repository, application, UI, database, and day-to-day workspace for:

- content discovery and research;
- reference/video ingestion;
- transcript storage and search;
- ideas;
- local high-fidelity speech-to-text (STT);
- diarization and speaker mapping;
- subtitle/text exports;
- text-to-speech (TTS);
- voice management;
- speech presets and history.

Speech Studio stops being a runtime dependency or separately operated product. Its useful capabilities are migrated into Content Radar. Heavy AI execution remains isolated from the normal API process inside the same repository and deployment.

The user experience must require one project, one frontend, one database, and one startup flow.

## 2. Core decision

The correct target is a **modular monorepo-style application**, not a remote integration between two repositories.

```text
Content-Radar/
├── frontend/                  # single Next.js UI
├── src/                       # main FastAPI app + business/data logic
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── speech/                # lightweight speech domain/orchestration
├── speech_worker/             # heavy local speech execution
│   ├── stt/
│   ├── tts/
│   ├── audio/
│   ├── runtime/
│   └── worker.py
├── speech_requirements/       # separated dependency sets
│   ├── base.txt
│   ├── stt-cpu.txt
│   ├── stt-cuda.txt
│   └── tts.txt
├── alembic/
├── tests/
└── docker-compose.yml
```

The **repository is unified** while **process boundaries remain deliberate**:

```text
Browser
  |
  v
Next.js frontend
  |
  v
Content Radar FastAPI
  |          |
  |          +---- PostgreSQL
  |
  +---- speech job queue/state
                |
                v
        local speech worker
          |           |
          |           +---- Piper / Kokoro / future TTS engines
          +---- WhisperX / pyannote / FFmpeg / Torch
```

This avoids installing CUDA/Torch/WhisperX into the web API image while still presenting a single product.

## 3. Why not merge everything into one Python process

Speech Studio's useful code includes a heavy ML stack: WhisperX, pyannote, PyTorch/CUDA, FFmpeg workflows and TTS engines such as Piper/Kokoro. These dependencies have different installation, hardware, startup, memory and failure characteristics from the Content Radar API.

A single-process merge would create avoidable problems:

- larger and slower backend image;
- GPU/CUDA dependency conflicts affecting research APIs;
- API startup failures if speech dependencies are unavailable;
- model memory remaining attached to the web process;
- difficult CPU/GPU deployment choices;
- harder tests because ordinary API tests would import ML packages;
- speech crashes potentially taking down Radar/Library/Ideas.

Therefore "one platform" means one repository and one controlled deployment, not one Python interpreter.

## 4. Product principles

1. **One main UI.** Speech Studio's existing frontend is not kept as a second daily-use application.
2. **Intent before parameters.** Normal use exposes understandable choices such as Rápido, Equilibrado and Máxima qualidade.
3. **Advanced controls are optional.** Technical parameters remain available with plain-language descriptions.
4. **Content Radar owns durable data.** Speech output becomes native Content Radar data.
5. **Worker owns execution, not truth.** The worker may produce temporary artifacts, but PostgreSQL and Content Radar models are authoritative.
6. **Graceful degradation.** Radar, Pesquisas, Biblioteca and Ideias continue working if speech execution is unavailable.
7. **No duplicated history.** Speech Studio's standalone database/history is not migrated as a second source of truth.
8. **No unnecessary production-suite expansion.** This is a research + speech workspace, not a video editor.
9. **Preserve high-fidelity behavior.** WhisperX alignment, diarization, VAD controls and useful exports survive migration.
10. **Migration over blind copy.** Existing Speech Studio code is adapted into focused modules rather than dropped into Content Radar unchanged.

## 5. Migration inventory

### 5.1 Migrate and refactor

From Speech Studio:

- `transcribe.py` pipeline logic;
- FFmpeg/audio conversion utilities;
- health/hardware checks relevant to speech execution;
- STT progress-stage parsing;
- diarization and speaker-profile logic;
- subtitle/text formatting/export behavior;
- TTS engine abstractions;
- Piper engine support;
- Kokoro engine support;
- Portuguese text preprocessing used by TTS;
- TTS registry/capability logic;
- text chunking;
- reusable preset concepts;
- artifact collection/output logic;
- useful job/progress semantics.

These are reorganized under `speech_worker/` or the Content Radar speech domain depending on whether they require heavy ML/runtime dependencies.

### 5.2 Reimplement against Content Radar infrastructure

Do **not** directly copy these as authoritative infrastructure:

- Speech Studio database/history implementation;
- standalone API route organization where it duplicates Content Radar routing;
- global filesystem paths that assume Speech Studio repository layout;
- standalone upload/output history model;
- standalone dashboard state;
- separate frontend application.

Equivalent behavior should use:

- Content Radar PostgreSQL + Alembic;
- Content Radar service/repository patterns;
- Content Radar API routes;
- Content Radar frontend components;
- scoped media/artifact storage owned by the unified app.

### 5.3 Keep only as temporary reference

- old console assistant / `.bat` launch workflow;
- old Speech Studio frontend;
- Gradio-only UI code;
- scripts whose only purpose was starting two separate apps.

These remain in the old repository until parity is achieved, then the repository can be archived manually.

## 6. Speech domain boundaries

### 6.1 Main API/domain (`src/speech/`)

Responsible for:

- validating user-facing requests;
- resolving presets into technical configuration;
- creating speech jobs;
- maintaining job state;
- deciding worker capability/fallback;
- linking jobs to references/transcripts;
- normalizing worker results;
- importing durable transcript data;
- speaker display mappings;
- personal presets;
- artifact metadata;
- user-facing errors.

It must not import WhisperX, torch, pyannote or heavy TTS libraries.

### 6.2 Worker (`speech_worker/`)

Responsible for:

- FFmpeg extraction/conversion;
- model loading;
- STT execution;
- alignment;
- diarization;
- TTS execution;
- progress reporting;
- creating temporary/generated artifacts;
- hardware introspection;
- returning structured results/errors.

The worker must not directly mutate Content Radar domain tables except through a tightly controlled job protocol. Prefer the main API/service layer as the only durable-data writer.

## 7. Job transport

For the first unified version, avoid adding Redis/Celery unless proven necessary.

Use PostgreSQL-backed speech jobs plus a worker claim loop:

1. API creates a `speech_jobs` row with `status='queued'`.
2. Worker polls/claims the next compatible queued job with row locking.
3. Worker changes it to `running` and updates stage/progress.
4. Worker writes structured result metadata/artifact references.
5. Main service finalizes/imports the result into transcript/TTS domain data.
6. Job becomes `completed` or `failed`.

This keeps deployment to PostgreSQL + backend + frontend + speech worker and avoids another infrastructure dependency.

Concurrency starts at **one heavy job at a time per worker**. The schema supports future multiple workers by ownership/lease fields.

Required job fields:

- `id`;
- `operation`: `stt` or `tts`;
- `status`: `queued`, `running`, `completed`, `failed`, `cancelled`;
- `stage`;
- `progress_percent`;
- `progress_message`;
- `requested_config_json`;
- `resolved_config_json`;
- `source_path` or managed input reference;
- optional `reference_source_id`;
- optional resulting `transcript_id`;
- worker id/lease fields;
- result/artifact metadata;
- normalized error code/message;
- debug log tail/path;
- timestamps.

## 8. STT modes and presets

Built-in presets are native Content Radar data/configuration, not Speech Studio remote presets.

### Rápido

For rough extraction and low-latency jobs.

Default intent:

- small model;
- int8;
- conservative batch size;
- no diarization unless explicitly enabled;
- normal VAD;
- word alignment optional based on worker path.

### Equilibrado

Default for ordinary videos and research references.

Default intent:

- medium model;
- int8 on constrained hardware;
- alignment enabled;
- optional diarization;
- safe batch based on detected hardware;
- normal VAD.

### Máxima qualidade

For interviews, podcasts, difficult audio and important references.

Default intent:

- prefer large-v3 when capability check says it is safe;
- otherwise fall back to medium;
- memory-safe compute/batch;
- alignment enabled;
- optional diarization;
- conservative resource use.

The UI always allows the user to inspect **Resolved configuration** so presets remain understandable rather than magical.

## 9. Guided STT controls

Normal questions map to technical values:

- "Idioma" -> `language`;
- "Identificar pessoas falando" -> diarization enabled;
- "Quantas pessoas?" -> exact `num_speakers` or range;
- "Há falas baixas/sussurradas?" -> sensitive VAD profile;
- "Há nomes/termos difíceis?" -> `initial_prompt`;
- "Prioridade" -> built-in/personal preset.

Advanced mode exposes:

- model;
- compute type;
- batch size;
- device;
- diarization;
- exact/min/max speakers;
- speaker profile;
- VAD onset/offset;
- chunk size;
- initial prompt;
- export formats.

Every technical field gets a short description, safe range and recommended value.

## 10. Hardware-aware resolution

The worker exposes capability data such as:

- CPU available;
- CUDA available;
- GPU name;
- approximate VRAM if detectable;
- installed STT engines/models capability;
- diarization readiness/token state;
- TTS engines available.

The preset resolver uses capability information to avoid knowingly dangerous configurations.

Examples:

- low VRAM + maximum quality -> large-v3/int8/batch 1 if supported, otherwise medium/int8/batch 1;
- CPU only -> avoid GPU-only settings and explain expected slowness;
- missing HF token/model access -> diarization unavailable but plain transcription still works;
- TTS engine not installed -> hide/disable that engine instead of failing after submit.

The user may override advanced values, but the UI should warn when they conflict with detected capability.

## 11. Transcript model integration

Speech transcription must end in Content Radar's existing transcript/versioning system.

Worker output is normalized to:

- language and confidence;
- engine (`whisperx`, `faster_whisper`, `youtube_captions`);
- model;
- preset/resolved configuration metadata;
- full text;
- segments with start/end/text;
- speaker labels when available;
- optional word list with start/end/score/speaker;
- raw engine metadata retained only where useful.

For a reference source:

1. create speech job linked to reference;
2. worker transcribes;
3. normalize result;
4. create new transcript version;
5. activate according to existing versioning rules;
6. run transcript topic enrichment;
7. make segments available to global search/deep links.

The existing lightweight `faster-whisper` path may remain initially as an internal mode, then can be unified behind the same speech orchestration interface.

## 12. Speaker mapping

Keep raw diarization labels immutable:

- `SPEAKER_00`;
- `SPEAKER_01`;
- etc.

Store a display mapping separately:

```text
SPEAKER_00 -> Gabriel
SPEAKER_01 -> João
```

Renaming does not rewrite raw transcript text/engine metadata.

Mappings can later be promoted into reusable speaker profiles, but initial scope is per transcript/job to avoid accidental identity assumptions.

## 13. Export behavior

Preserve useful Speech Studio exports:

- TXT;
- JSON;
- SRT;
- VTT.

Exports are generated from normalized data when possible rather than treated as the canonical result.

Subtitle formatting preserves the useful behavior already present in Speech Studio:

- speaker-aware splitting;
- readable line limits;
- timestamp formatting;
- silence/speaker-change boundaries;
- bounded subtitle durations.

Artifacts are exposed through safe Content Radar download endpoints, never raw worker filesystem paths.

## 14. TTS architecture

TTS becomes the second half of the Audio module.

The worker contains engine implementations migrated from Speech Studio:

```text
speech_worker/tts/
├── base.py
├── registry.py
├── piper_engine.py
├── kokoro_engine.py
├── ptbr_text.py
└── text_chunking.py
```

Main API exposes engine-neutral concepts:

- selected engine;
- voice;
- language;
- speed;
- optional engine-specific advanced settings;
- input text;
- generated artifact.

The frontend presents only engines currently reported as available by worker capabilities.

Do not expose the raw engine registry directly to UI code.

## 15. Voice management

The unified platform distinguishes:

- built-in/discovered voices supplied by an engine;
- locally installed voice assets;
- user-friendly saved voice presets.

Voice metadata belongs in Content Radar if it is user-created configuration. Large model/voice binary files remain on managed storage, not in PostgreSQL or Git.

The system stores paths/identifiers safely and verifies availability before execution.

## 16. Personal presets

Create native personal presets for STT first and TTS later.

A preset stores:

- name;
- operation type;
- user-facing description;
- complete configuration JSON;
- created/updated timestamps;
- built-in flag.

Built-ins are code/seed controlled and cannot be deleted. Personal presets can be created, copied, edited and deleted.

A "save current configuration as preset" action is part of the advanced/guided UI.

## 17. Audio UI

Add one sidebar item: **Áudio**.

Primary route:

`/audio`

Tabs/sections:

1. **Transcrever**
2. **Gerar voz**
3. **Histórico**
4. **Presets**
5. **Vozes**

### Transcrever

Default surface:

```text
Arquivo
[ selecionar/arrastar ]

Qualidade
[ Equilibrado ]

Idioma
[ Automático ]

[ ] Identificar pessoas falando

[ Transcrever ]
```

Expandable sections:

- Opções guiadas;
- Configuração avançada;
- Configuração resolvida.

### Result view

Shows:

- status/progress;
- duration/language/model;
- detected speakers;
- speaker rename controls;
- timestamped transcript;
- copy plain text;
- export TXT/SRT/VTT/JSON;
- save/import into Biblioteca where applicable;
- advanced logs collapsed by default.

## 18. Biblioteca integration

YouTube import/transcription choices become conceptually:

- Automático;
- Legenda do YouTube;
- Local rápido;
- Local equilibrado;
- Local máxima qualidade.

"Automático" should prefer cheap/available captions before expensive local STT unless user settings explicitly change that policy.

Manual audio/video files can also be added directly through Áudio and optionally promoted to a Biblioteca reference.

## 19. Storage layout

Introduce managed application storage, configurable by environment:

```text
data/
└── speech/
    ├── inputs/
    ├── jobs/
    ├── artifacts/
    ├── models-or-links/
    └── voices/
```

Rules:

- temp converted WAV files are deleted after completion unless debugging retention is enabled;
- original uploaded files have explicit retention policy;
- generated final artifacts remain only while referenced or per cleanup policy;
- filenames are server-generated/sanitized;
- no arbitrary paths from requests;
- browser downloads go through validated API endpoints.

## 20. Database changes

New tables (names may be refined during implementation plan but semantics are fixed):

### `speech_jobs`

Durable queue/progress/result state.

### `speech_presets`

User-created STT/TTS presets.

### `transcript_speaker_mappings`

Display mapping from raw speaker id to chosen name for a transcript.

### `speech_artifacts`

Metadata for downloadable generated/imported artifacts.

Optional later table:

### `speech_voice_presets`

Only if TTS voice preset data cannot cleanly live in `speech_presets`.

No new separate SQLite database from Speech Studio is introduced.

## 21. API design

All public browser-facing APIs are Content Radar APIs.

Examples:

```text
GET    /speech/capabilities
GET    /speech/presets
POST   /speech/presets
PATCH  /speech/presets/{id}
DELETE /speech/presets/{id}

POST   /speech/jobs/stt
POST   /speech/jobs/tts
GET    /speech/jobs
GET    /speech/jobs/{id}
POST   /speech/jobs/{id}/cancel

GET    /speech/jobs/{id}/artifacts
GET    /speech/artifacts/{id}/download

PATCH  /transcripts/{id}/speakers/{speaker_id}
```

The worker protocol is internal and not called directly by the frontend.

## 22. Worker protocol

Prefer direct PostgreSQL job claiming for the initial version rather than a second HTTP API.

Worker responsibilities:

- claim queued jobs using safe row locking;
- heartbeat/lease while running;
- update progress fields;
- write result JSON/artifact metadata;
- never expose itself publicly;
- recover abandoned leases after a timeout;
- gracefully stop after current job on shutdown.

This replaces the previous `SPEECH_STUDIO_BASE_URL` architecture.

## 23. Dependency strategy

Main Content Radar `requirements.txt` remains comparatively light.

Heavy dependencies are separated:

- worker base audio dependencies;
- STT CPU profile;
- STT CUDA profile;
- TTS profile.

Do not force CUDA packages onto CPU-only installs.

The exact WhisperX/Torch install procedure should be retained/adapted from Speech Studio's working scripts instead of casually pinning incompatible versions during migration.

FFmpeg remains an explicit runtime requirement for the speech worker.

## 24. Docker/developer startup

Target normal workflow:

```powershell
docker compose up -d --build
```

Services:

- postgres;
- migrate;
- backend;
- frontend;
- speech-worker when configured for container execution.

However, GPU execution on Windows may be easier to keep as a **repo-owned host worker command** initially if Docker GPU passthrough complicates the proven Speech Studio environment.

Therefore the unified repo supports two worker runtimes behind the same PostgreSQL job protocol:

### Mode A — host worker (first-class)

```powershell
.\scripts\speech-worker.ps1
```

Uses local `.venv-speech`, local NVIDIA/CUDA stack and the same Content Radar database.

### Mode B — Docker worker

Available when compatible NVIDIA container runtime is configured.

The application remains one repository either way. The user does not need to clone or operate Speech Studio separately.

## 25. Installation UX

Provide repository-owned installation helpers rather than preserving Speech Studio launch scripts unchanged:

```text
scripts/
├── install-speech-cpu.ps1
├── install-speech-gpu.ps1
├── install-speech-tts.ps1
├── speech-worker.ps1
└── check-speech.ps1
```

`check-speech.ps1` should report understandable readiness:

```text
FFmpeg ............... OK
Python speech env .... OK
CUDA .................. OK (RTX ...)
WhisperX .............. OK
Diarization ........... unavailable: configure HF_TOKEN
Piper .................. OK
Kokoro ................. not installed
```

The frontend capability page mirrors this information when the worker has reported it.

## 26. Error model

Normalize technical failures into stable error codes and user messages:

- `worker_unavailable`;
- `engine_not_installed`;
- `ffmpeg_missing`;
- `invalid_media`;
- `insufficient_vram`;
- `model_load_failed`;
- `diarization_unavailable`;
- `hf_access_required`;
- `transcription_failed`;
- `tts_failed`;
- `artifact_failed`;
- `job_cancelled`.

Raw traceback/log output is stored for debug but not shown as the primary UI error.

## 27. Migration order

Migration must be incremental so Content Radar stays usable after every phase.

### Phase 0 — remove wrong remote-integration direction

- preserve useful preset schemas/resolution tests;
- remove/deprecate `SpeechStudioClient` and `SPEECH_STUDIO_BASE_URL`;
- mark previous remote-integration docs superseded;
- keep regression green.

### Phase 1 — unified speech domain + job foundation

- migrations/tables;
- job service;
- preset persistence;
- capability snapshot model;
- worker protocol contract;
- tests without ML dependencies.

### Phase 2 — migrate STT worker core

- audio/FFmpeg utilities;
- refactor `transcribe.py` into modules;
- WhisperX execution;
- alignment;
- diarization;
- progress/error normalization;
- TXT/JSON/SRT/VTT generation;
- CPU/GPU install scripts;
- worker tests around pure logic + contract tests.

### Phase 3 — Audio STT UI

- `/audio`;
- file upload;
- presets;
- guided/advanced settings;
- job progress;
- transcript result view;
- exports;
- speaker mappings.

### Phase 4 — Biblioteca integration

- local STT modes for YouTube/reference imports;
- normalize into transcript versioning;
- search/deep-link compatibility;
- topic enrichment;
- dedup semantics preserved.

### Phase 5 — migrate TTS

- engine abstractions;
- Piper/Kokoro;
- voice discovery;
- text preprocessing/chunking;
- TTS jobs/artifacts;
- Generate Voice UI.

### Phase 6 — history/presets/voices polish

- speech-specific history;
- personal presets complete;
- voice management;
- hardware-aware recommendations;
- cleanup/retention tooling.

### Phase 7 — retire old Speech Studio

Only after parity verification:

- document that Content Radar is authoritative;
- archive old Speech Studio repositories manually if desired;
- no runtime references to them remain.

## 28. Testing strategy

### Pure/unit tests

Must not require GPU/models:

- preset resolution;
- hardware-safe fallback decisions;
- job state transitions;
- queue claim/lease behavior;
- artifact naming/path safety;
- subtitle grouping;
- transcript normalization;
- speaker mappings;
- TTS chunking/text preprocessing;
- error normalization.

### Database integration tests

- job creation/claim/completion;
- lease recovery;
- transcript version creation from STT result;
- reference linkage;
- presets persistence;
- artifact lifecycle metadata;
- speaker mappings.

### Worker contract tests

Use fake engines to prove:

- progress sequence;
- cancellation;
- result schema;
- error schema;
- capability reporting.

### Optional real-engine smoke tests

Not part of ordinary CI/test battery because models/GPU are heavy:

- one short STT file without diarization;
- one diarized file when HF/CUDA available;
- one Piper/Kokoro generation per installed engine.

### Frontend

- typecheck/build;
- preset form behavior;
- guided/advanced visibility;
- progress/error display;
- speaker rename interaction;
- engine unavailable states.

### Regression gate

Existing Content Radar test suite remains green after each phase. The current baseline after the remote-integration foundation is 61 passing tests; this is the starting safety net before architecture replacement.

## 29. Security/privacy

- `HF_TOKEN` and future secrets are server/worker only;
- no secret is returned to browser;
- upload paths are generated and constrained;
- file type/size validation is mandatory;
- no arbitrary filesystem read/download endpoint;
- raw worker paths never become public URLs;
- temporary media is cleaned up;
- media remains local unless another explicit provider is later added.

## 30. Observability

Each speech job should expose enough detail to answer:

- what is running;
- which stage;
- which preset/config was resolved;
- which worker claimed it;
- when progress last changed;
- what failed;
- where the final result belongs.

Keep debug logs bounded so database rows do not grow indefinitely. Full logs may be written to managed files with only a tail/error summary stored in PostgreSQL.

## 31. Cancellation and recovery

Cancellation semantics:

- queued job -> cancel immediately;
- running job -> set cancellation requested; worker checks between major stages and terminates subprocess/model task where safe;
- completed/failed jobs cannot become cancelled retroactively.

Crash recovery:

- worker uses lease/heartbeat;
- expired running jobs can return to queued or fail with explicit recovery reason based on retry count;
- maximum automatic retry count is conservative (default 1 for heavy inference) to avoid infinite expensive loops.

## 32. Compatibility with existing transcription

The current Content Radar transcription paths remain operational while the worker migration is incomplete.

The target common abstraction is conceptually:

```python
TranscriptionRequest -> TranscriptionResult
```

Providers/engines:

- YouTube captions;
- current faster-whisper local fallback;
- unified WhisperX worker.

This enables migration without a flag day and lets "Automático" choose an appropriate strategy.

## 33. What is deliberately not copied

Do not carry forward technical debt merely for parity:

- separate Speech Studio SQLite/history DB;
- separate Vite/Gradio/Streamlit UI as a supported product;
- duplicate API server;
- duplicated upload/history stores;
- raw subprocess commands assembled inside public API route functions;
- hard-coded repository-specific paths;
- requirement that Content Radar know a remote Speech Studio base URL.

## 34. Explicit non-goals

- video editing/timeline editor;
- automated full video production;
- cloud speech billing/provider abstraction in this phase;
- multi-user authentication/permissions;
- distributed multi-machine worker fleet;
- Redis/Celery unless PostgreSQL queue proves insufficient;
- vector database;
- automatic voice identity recognition from diarization;
- merging heavy ML dependencies into FastAPI web process.

## 35. Acceptance criteria

The merge is complete when all of the following are true:

1. The user clones/opens only Content Radar for normal work.
2. Speech Studio repository is not required at runtime.
3. One Content Radar frontend exposes research, references, ideas and Audio.
4. STT supports quick/balanced/max-quality presets plus advanced controls.
5. High-fidelity local STT preserves WhisperX alignment and optional pyannote diarization.
6. Transcript results become native Content Radar transcript versions and searchable segments.
7. Speaker mappings are editable without destroying raw labels.
8. TXT/JSON/SRT/VTT exports are available safely.
9. TTS supports migrated Piper/Kokoro capabilities that are actually installed.
10. Hardware/readiness is understandable without remembering CLI flags.
11. Backend remains usable when speech worker is offline.
12. Heavy speech dependencies are isolated from the main API environment.
13. No second speech history/database/frontend is authoritative.
14. Existing Content Radar regression suite remains green through migration.
15. Real-engine smoke tests pass on the user's actual local speech environment before the old Speech Studio is considered retired.

## 36. SDD execution rule

This spec is authoritative for the merge. Implementation must be split into phase-specific plans rather than one giant plan. Each phase follows:

1. define exact file ownership/interfaces;
2. write failing tests first;
3. implement smallest passing slice;
4. run focused tests;
5. run relevant regression tests;
6. commit checkpoint;
7. verify acceptance criteria for that phase before moving on.

The first implementation plan after approval must cover only **Phase 0 + Phase 1**. STT ML migration starts in a separate plan after the unified domain/job foundation is verified.