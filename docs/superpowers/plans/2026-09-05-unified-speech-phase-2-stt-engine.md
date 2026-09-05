# Unified Speech Suite Phase 2 — Native STT Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate Speech Studio's high-fidelity STT pipeline into Content Radar's native `speech_worker`, including FFmpeg conversion, WhisperX transcription, alignment, optional pyannote diarization, word-level normalization, TXT/JSON/SRT/VTT exports, job progress, cancellation, artifacts, and worker capability reporting.

**Architecture:** The main FastAPI process remains free of WhisperX/Torch/pyannote imports. Heavy STT code lives under `speech_worker/stt/`, consumes native `SpeechJob` rows created in Phase 1, writes temporary/generated files only under managed speech storage, and returns normalized structured results to the Content Radar job domain. Speech Studio's standalone history/database/frontend are not migrated.

**Tech Stack:** Python 3.12 worker process, PostgreSQL/SQLAlchemy queue from Phase 1, FFmpeg, WhisperX, PyTorch, pyannote via WhisperX diarization, Hugging Face models/token, pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-05-unified-speech-suite-design.md`

## Global Constraints

- Content Radar is the only repository/product/runtime entrypoint.
- No HTTP dependency on the Speech Studio repository.
- Heavy ML imports must never be imported by `src/api/*`, ordinary backend startup, or non-speech unit tests.
- STT worker input/output paths must remain inside `SPEECH_DATA_ROOT` managed storage.
- Existing `SpeechJob` queue/lease/cancellation semantics from Phase 1 remain authoritative.
- Worker output must be normalized before becoming durable Content Radar transcript data.
- Alignment failure must degrade to transcription timestamps rather than fail the entire job.
- Missing/invalid diarization prerequisites must degrade to non-diarized transcript when transcription itself succeeded.
- Cancellation checks occur between expensive stages and before finalization.
- Temporary converted WAV files are removed on terminal completion unless explicit debug retention is enabled.
- TXT/JSON/SRT/VTT are derived artifacts; normalized result JSON is canonical worker output.
- Preserve the existing Content Radar transcript versioning/enrichment flow when a speech job is linked to a reference.

---

## Locked file map

### Worker STT modules
- Create: `speech_worker/stt/__init__.py`
- Create: `speech_worker/stt/types.py`
- Create: `speech_worker/stt/audio.py`
- Create: `speech_worker/stt/subtitles.py`
- Create: `speech_worker/stt/normalize.py`
- Create: `speech_worker/stt/engine.py`
- Create: `speech_worker/stt/errors.py`
- Modify: `speech_worker/runtime/capabilities.py`
- Modify: `speech_worker/runtime/executor.py`
- Modify: `speech_worker/worker.py`

### Main app integration
- Create: `src/services/speech_result_importer.py`
- Modify: `src/repositories/speech_jobs.py`
- Modify: `src/services/speech_jobs_service.py`
- Modify: `src/models/reference.py` only if a source-method constraint must be extended for `whisperx`
- Create migration only if needed for transcript source-method constraint; do not mutate an already-applied 0019.

### Dependencies/deployment
- Create: `Dockerfile.speech`
- Create: `speech_requirements/base.txt`
- Create: `speech_requirements/stt.txt`
- Modify: `docker-compose.yml`
- Modify: `.env.example`

### Tests
- Create: `src/test_speech_stt_audio.py`
- Create: `src/test_speech_subtitles.py`
- Create: `src/test_speech_stt_normalize.py`
- Create: `src/test_speech_stt_engine.py`
- Create: `src/test_speech_result_importer.py`
- Modify: `src/test_speech_worker_protocol.py`
- Modify: `src/test_speech_api.py` only for capability/status assertions.

---

### Task 1: Isolate STT types and errors

**Produces:**
- `SttResolvedConfig`
- `NormalizedWord`
- `NormalizedSegment`
- `NormalizedTranscriptResult`
- `SttEngineError`, `SttCancelled`, `SttNoSpeech`, `SttModelLoadError`

`NormalizedTranscriptResult` fields:

```python
language: str | None
engine: str = "whisperx"
model: str
full_text: str
segments: list[NormalizedSegment]
diarized: bool
alignment_used: bool
warnings: list[str]
raw_metadata: dict[str, Any]
```

Each segment contains `index`, `start`, `end`, `text`, `speaker`, and `words`; each word contains `word`, `start`, `end`, optional `score`, optional `speaker`.

Tests verify Pydantic/dataclass shape and JSON-serializable output without importing WhisperX.

---

### Task 2: Migrate FFmpeg audio conversion into managed worker utility

**Produces:** `convert_to_wav(input_path, output_path, runner=subprocess.run) -> Path`.

Command must be equivalent to:

```text
ffmpeg -y -i INPUT -vn -acodec pcm_s16le -ar 16000 -ac 1 OUTPUT
```

Rules:
- reject missing input;
- parent directories are created by caller/storage;
- raise typed error on missing FFmpeg or non-zero exit;
- never create paths outside caller-supplied managed path;
- cancellation is checked before and after conversion.

Unit tests inject a fake runner, assert exact command construction, missing-file error and failed-conversion error.

---

### Task 3: Migrate subtitle card generation and exporters

Refactor the proven Speech Studio functions into pure code:
- `format_timestamp()`
- `format_words_into_lines()`
- `group_words_into_cards()`
- `split_segment_without_words()`
- `format_card_for_subtitle()`
- `render_txt()`
- `render_srt()`
- `render_vtt()`
- `render_json()`

Exporters return strings/bytes; filesystem writing belongs to the executor/storage layer.

Tests cover:
- speaker change splits a card;
- silence >1.5s splits a card;
- max 2 lines / 42 chars behavior;
- SRT comma milliseconds;
- VTT dot milliseconds and WEBVTT header;
- speaker names only included when diarization exists;
- fallback proportional segmentation without word timestamps.

---

### Task 4: Add normalization from WhisperX-shaped dictionaries

**Produces:**

```python
normalize_whisperx_result(raw, *, model, diarized, alignment_used, warnings) -> NormalizedTranscriptResult
```

Rules:
- trim empty segments;
- preserve repeated spoken text; no semantic dedupe;
- sort by start time while preserving original order for ties;
- full text is joined from normalized segment text;
- missing word start/end remains `None` rather than fabricated in canonical data;
- subtitle layer may fabricate proportional timing only for display/export;
- speaker defaults to `None`, not the literal `UNKNOWN`, in canonical normalized data;
- retain useful language/duration metadata, not arbitrary unserializable ML objects.

---

### Task 5: Implement WhisperX engine with stage-level degradation

Create `WhisperXSttEngine.transcribe(input_wav, config, progress_callback, cancel_check) -> NormalizedTranscriptResult`.

Sequence:

1. resolve device (`auto` -> CUDA when torch reports available, otherwise CPU);
2. progress `loading_model` 15%;
3. `whisperx.load_model(model, device, compute_type, asr_options, vad_options)`;
4. progress `transcribing` 30%;
5. `model.transcribe(... batch_size, language)`;
6. release ASR model and GPU cache;
7. if no segments, raise `SttNoSpeech`;
8. alignment at 55%; on failure append warning and continue with raw transcript;
9. diarization at 75% only when enabled + token available; on failure append warning and continue aligned/raw transcript;
10. assign word speakers when diarization succeeds;
11. normalize result;
12. progress `normalizing` 90%.

Cancellation checks: before model load, after transcription, after alignment, after diarization.

Do not import WhisperX/Torch at module import time. Imports occur inside engine methods so backend/unit-test imports stay light.

Tests mock `sys.modules`/loader adapters to verify:
- happy path with alignment+diarization;
- alignment failure degrades;
- missing HF token skips diarization with warning;
- diarization exception degrades;
- no speech raises typed result;
- cancellation interrupts between stages;
- models are released/cleanup hook called.

---

### Task 6: Wire real STT into `SpeechExecutor`

`SpeechExecutor.execute()` now supports `operation == "stt"` when capability says STT ready.

Execution flow:
- validate `job.input_path` belongs to managed storage root;
- derive work WAV path and artifact paths through `SpeechStorage`;
- convert source media to WAV;
- call `WhisperXSttEngine`;
- render JSON/TXT/SRT/VTT according to resolved config formats;
- create files under `jobs/<id>/artifacts/`;
- return structured result:

```python
{
  "kind": "stt",
  "normalized": result.model_dump(),
  "artifacts": [
    {"artifact_type": "json", "storage_key": ..., "filename": ..., "mime_type": ...},
    ...
  ]
}
```

Finally remove temporary WAV unless `SPEECH_KEEP_WORK_FILES=true`.

---

### Task 7: Register artifacts and import completed STT into Content Radar transcripts

Add repository helpers to create `SpeechArtifact` rows idempotently for a completed job.

Create `SpeechResultImporter.finalize_stt_job(job)`:
- validate completed STT result shape;
- persist artifact metadata;
- if no `reference_source_id`, stop after job/artifacts;
- if linked reference: create transcript version using normalized full text + segments;
- source method must be a native accepted value (`whisperx` preferred); if current DB constraint blocks it, add a new Alembic migration changing the constraint rather than hiding WhisperX under legacy `audio_to_text_future`;
- preserve duplicate/versioning behavior from existing references service;
- activate new transcript using existing rules;
- run transcript topic enrichment;
- set `speech_jobs.transcript_id`.

Tests cover manual audio job (no reference), linked reference import, segments+speaker+word tokens, and idempotent finalization.

---

### Task 8: Worker capabilities and readiness

Capability detection must report:
- Python worker online;
- FFmpeg availability;
- WhisperX import availability;
- torch availability;
- CUDA availability;
- GPU name and VRAM when safely detectable;
- `stt_ready = ffmpeg_available and whisperx_available and torch_available`;
- `diarization_ready = stt_ready and HF_TOKEN configured` (model access can still fail at runtime and becomes warning/error detail).

Heavy imports remain lazy. Capability probing may use `importlib.util.find_spec`, `shutil.which`, and a guarded torch import only inside worker process.

Worker operations becomes `["stt"]` only when `stt_ready` is true.

---

### Task 9: Create dedicated speech worker image/dependency boundary

`Dockerfile.speech`:
- base Python 3.12 slim;
- install `ffmpeg`, `git`, minimal runtime system libs;
- install normal Content Radar requirements needed by SQLAlchemy/worker;
- install `speech_requirements/stt.txt`;
- copy repository;
- default command `python -m speech_worker.worker`.

`speech_requirements/base.txt` contains light speech-specific packages not already in root requirements.

`speech_requirements/stt.txt` installs WhisperX and its ML dependencies only in speech image. The main backend Dockerfile/requirements remain unchanged.

Compose changes `speech_worker` to `dockerfile: Dockerfile.speech` and shares `./data:/app/data`.

Environment additions:

```env
HF_TOKEN=
HF_HOME=/app/data/speech/models/huggingface
SPEECH_KEEP_WORK_FILES=false
SPEECH_DIARIZE_MODEL=pyannote/speaker-diarization-3.1
```

No Speech Studio variables are reintroduced.

---

### Task 10: End-to-end worker finalization flow

Update `run_once()`:
- heartbeat worker state;
- recover stale leases;
- claim only supported operations;
- execute;
- mark complete;
- call result finalizer in same process with a fresh/valid DB session transaction;
- if finalizer fails after engine success, mark job `failed` with `result_import_error` unless already terminal in a recoverable finalized state;
- cancellation produces `cancelled`, not generic failed.

Test with fake engine/storage/repository, no ML dependencies.

---

### Task 11: Verification gate

Targeted light tests in backend image:

```powershell
docker compose run --rm --no-deps backend sh -lc "pip install pytest && python -m pytest \
src/test_speech_presets.py \
src/test_speech_job_models.py \
src/test_speech_storage.py \
src/test_speech_job_repository.py \
src/test_speech_jobs_service.py \
src/test_speech_worker_protocol.py \
src/test_speech_stt_audio.py \
src/test_speech_subtitles.py \
src/test_speech_stt_normalize.py \
src/test_speech_stt_engine.py \
src/test_speech_result_importer.py \
src/test_speech_api.py -v"
```

Build heavy worker separately:

```powershell
docker compose build speech_worker
```

Capability smoke:

```powershell
docker compose up -d speech_worker backend
Invoke-RestMethod http://localhost:8000/speech/status | ConvertTo-Json -Depth 8
```

Real STT smoke is performed only after worker reports `stt_ready=true`. Use a small user-owned/public-domain audio file, create a managed upload/job through the Content Radar path, then verify job reaches `completed`, artifacts exist and linked references receive a transcript.

Finally rerun the previous full Content Radar regression suite before declaring Phase 2 complete.
