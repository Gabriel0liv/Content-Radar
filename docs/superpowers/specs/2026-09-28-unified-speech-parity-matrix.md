# Unified Speech Suite Parity Matrix

This document records the migration of useful Speech Studio capabilities into the native Content Radar Speech Suite.

## Status legend

- **Migrated** — available natively in Content Radar.
- **Replaced** — legacy behavior exists through a different native workflow.
- **Environment-dependent** — implemented, but requires optional local runtime/model dependencies.
- **Excluded** — deliberately not carried forward.

## Core architecture

| Legacy capability | Native Content Radar replacement | Status | Notes |
|---|---|---|---|
| Separate Speech Studio app | `/audio` workspace + FastAPI speech API | Replaced | No iframe/proxy runtime and no second frontend. |
| Local speech job execution | PostgreSQL-backed `speech_jobs` queue | Migrated | Uses lease, heartbeat, cancellation, retry and worker state. |
| Local SQLite history | PostgreSQL speech history | Replaced | Shared durable history with filtering/archive/retry. |
| Direct filesystem result paths | Managed speech storage + validated artifact download | Replaced | Browser never receives unrestricted `file://` paths. |
| Speech settings in isolated app | Native Speech settings API/UI | Migrated | Secrets are represented by presence/status only. |

## STT / transcription

| Capability | Status | Native behavior |
|---|---|---|
| WhisperX transcription | Environment-dependent | Executed only by `speech_worker`; API process stays lightweight. |
| Audio/video upload | Migrated | Managed staging with filename/path validation. |
| Multi-file/batch transcription | Migrated | Browser can select multiple media files; each upload becomes an independent durable job sharing the selected STT configuration. |
| Recursive local-directory CLI mode | Replaced | The browser does not receive unrestricted filesystem traversal. Multi-file upload provides the safe native batch workflow; server-side jobs remain managed individually. |
| MP3/WAV/MP4/MKV/MOV/M4A/WEBM inputs | Migrated | Server validation remains authoritative. |
| Presets | Migrated | Built-in and personal STT presets. |
| Model selection | Migrated | Resolved into durable worker config. |
| CPU/CUDA selection | Migrated | Capability-aware worker configuration. |
| Compute type | Migrated | `int8`, `float16`, `float32` according to runtime. |
| Batch size | Migrated | Advanced STT option. |
| VAD onset/offset | Migrated | Advanced STT option plus quiet-speech convenience mode. |
| Chunk size | Migrated | Worker-facing resolved option. |
| Language hint | Migrated | Guided STT control. |
| Initial prompt | Migrated | Guided STT control. |
| Speaker diarization | Environment-dependent | Requires compatible WhisperX/pyannote runtime and HF access where needed. |
| Fixed/min/max speaker count | Migrated | Durable request validation. |
| Offline/cache configuration | Migrated | Advanced worker configuration. |
| TXT export | Migrated | Managed artifact. |
| JSON export | Migrated | Managed artifact. |
| SRT export | Migrated | Managed artifact. |
| VTT export | Migrated | Managed artifact. |
| Speaker-aware subtitles | Migrated | Rendered without mutating raw speaker labels. |
| Rename speaker labels for display | Migrated | Display mapping is separate from immutable `SPEAKER_XX` metadata. |
| Biblioteca integration | Migrated | Completed STT can create/link transcript data through existing references infrastructure. |
| Cancellation | Migrated | Durable cancellation with worker checks between heavy stages. |

## TTS

| Capability | Status | Native behavior |
|---|---|---|
| Kokoro engine | Environment-dependent | Native worker engine adapter. |
| Piper engine | Environment-dependent | Native worker engine adapter. |
| PT-BR voice aliases | Migrated | Canonical native voice registry. |
| Text chunking | Migrated | Deterministic worker chunking for long text. |
| WAV output | Migrated | Managed artifact. |
| MP3 output | Environment-dependent | Requires FFmpeg. |
| Speed control | Migrated | Durable TTS request option. |
| Preview generation | Migrated | Separate preview job path using bounded effective text. |
| Full generation | Migrated | Durable TTS job. |
| PT-BR text analysis | Migrated | Lightweight API path; advisory only. |
| PT-BR normalization | Migrated | Explicit opt-in; original requested text remains preserved. |
| Engine/voice preset | Migrated | Personal TTS presets use the native preset store. |
| Per-engine missing dependency messages | Migrated | Normalized capability/unavailable reasons. |
| Voice sample generation | Migrated | Durable TTS jobs and managed sample assets. |
| Generate samples for all voices | Migrated | Native multi-job action exposed in the Voices/models UI. |
| PT-BR voice comparison | Migrated | Durable comparison workflow with per-voice result and report artifacts. |
| JSON comparison report | Migrated | Managed report artifact. |
| Markdown comparison report | Migrated | Optional managed report artifact. |

## Runtime visibility and diagnostics

| Capability | Status | Native behavior |
|---|---|---|
| FFmpeg detection | Migrated | Worker capability probe. |
| eSpeak detection | Migrated | Worker capability probe. |
| Torch detection | Migrated | Worker capability probe. |
| CUDA detection | Migrated | Worker capability probe. |
| GPU name / VRAM | Migrated | Persisted normalized worker capability data. |
| WhisperX readiness | Migrated | Persisted worker capability state. |
| Diarization readiness | Migrated | Distinguishes STT readiness from HF/diarization readiness. |
| Piper/Kokoro readiness | Migrated | Per-engine availability/reason. |
| Diagnostic checks | Migrated | Native `/audio` diagnostics view over real runtime state. |
| Health/status | Migrated | Queue and worker heartbeat/capabilities exposed by native API. |

## History, dashboard and artifact management

| Capability | Status | Native behavior |
|---|---|---|
| Dashboard: transcriptions/TTS today | Migrated | Native dashboard counts durable STT/TTS jobs created today. |
| Dashboard: total/completed/failed/success rate | Migrated | Derived from PostgreSQL speech history. |
| Dashboard: voices/storage/queue/runtime | Migrated | Uses real voice capabilities, managed storage size and worker/queue state. |
| Dashboard: recent and active jobs | Migrated | Native overview exposes recent durable jobs and current progress without filesystem paths. |
| Job history | Migrated | Newest-first PostgreSQL history. |
| Filter by operation/status | Migrated | Native history API/UI. |
| Retry | Migrated | Creates a new durable job linked through `retry_of_job_id`. |
| Archive history entry | Migrated | Non-destructive archive semantics. |
| Artifact download | Migrated | Validated managed path only. |
| Explicit artifact deletion | Migrated | Separate destructive action; no silent transcript deletion. |
| Active progress | Migrated | Stage, percentage, message and worker heartbeat. |
| Error details | Migrated | Normalized error code/message stored on durable job. |

## Frontend

| Legacy area | Native area | Status |
|---|---|---|
| Dashboard | `/audio` → Visão geral | Migrated |
| STT page | `/audio` → Transcrever | Migrated |
| TTS page | `/audio` → Gerar voz | Migrated |
| Voice browser | `/audio` → Vozes e modelos | Migrated |
| Presets | `/audio` → Presets | Migrated |
| History | `/audio` → Histórico | Migrated |
| Diagnostics | `/audio` → Diagnóstico | Migrated |
| Settings | `/audio` → Configurações | Migrated |
| Overall runtime state | `/audio` → Visão geral | Migrated |

The global sidebar exposes a single **Áudio** entry rather than duplicating every speech subsection globally.

## Deliberately excluded legacy behavior

| Legacy behavior | Status | Reason |
|---|---|---|
| Separate Gradio application as the normal user interface | Excluded | `/audio` is the canonical native workspace. |
| SQLite as canonical speech history | Excluded | PostgreSQL is the shared durable store. |
| Arbitrary local file URLs exposed to browser | Excluded | Managed storage/download boundary is required. |
| Unrestricted recursive browser access to arbitrary local folders | Excluded | Browser-side batch selection replaces direct filesystem traversal while preserving managed-storage boundaries. |
| Heavy ML imports inside the main FastAPI process | Excluded | Heavy engines stay isolated in `speech_worker`. |
| Secret token echo through settings/status APIs | Excluded | Only presence/readiness state is exposed. |
| Automatic model/GPU requirements in standard CI | Excluded | CI verifies non-heavy contracts; real runtime smokes are opt-in. |

## Runtime acceptance commands

After migrations, backend dependencies and the full speech worker runtime are installed:

```powershell
$env:PYTHONPATH="."
python scripts/speech_stt_smoke.py .\path\to\small-audio.wav --preset fast --language pt
python scripts/speech_tts_smoke.py --engine kokoro --preview
python scripts/speech_tts_smoke.py --engine piper --preview
```

Exit codes for the runtime smoke scripts:

- `0`: real runtime execution passed.
- `1`: implementation/runtime regression detected.
- `2`: required optional runtime/engine is unavailable in the current environment (`SKIP`).

A `2` is not evidence that the corresponding engine works; it records an environment limitation distinctly from a regression failure.
