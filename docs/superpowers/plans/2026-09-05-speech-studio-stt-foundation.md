# Speech Studio STT Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested Content Radar integration foundation for Speech Studio STT, including engine health, user-friendly STT preset resolution, request construction, and a small backend API that the future `/audio` UI can consume.

**Architecture:** Content Radar remains the owning application and talks to Speech Studio only through a dedicated `SpeechStudioClient`. A separate STT preset resolver converts user intent (`fast`, `balanced`, `max_quality`) plus guided options into the raw Speech Studio form parameters. This phase does not import WhisperX/PyTorch into Content Radar and does not yet build TTS, voices, or full job persistence.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, HTTPX, pytest, existing Content Radar Docker/PostgreSQL stack, Speech Studio FastAPI service.

**Spec:** `docs/superpowers/specs/2026-09-05-speech-studio-integration-design.md`

## Global Constraints

- Content Radar is the single primary frontend.
- Speech Studio remains a separate runtime/service.
- Do not add WhisperX, pyannote, PyTorch, or CUDA dependencies to the Content Radar backend.
- Content Radar core features must continue working when Speech Studio is offline.
- Normal users select intent/quality; raw parameters stay behind a resolver and an advanced surface.
- Built-in STT presets are `fast`, `balanced`, and `max_quality`.
- The first phase is STT integration only; TTS, voices, and platform-wide activity history are explicitly deferred.
- `SPEECH_STUDIO_BASE_URL` is the runtime integration boundary.

---

## File Structure

- Create `src/schemas/speech.py` — request/response models shared by speech routes and services.
- Create `src/services/speech_presets.py` — built-in STT preset definitions and guided-option resolution.
- Create `src/services/speech_studio_client.py` — all HTTP communication/error normalization with Speech Studio.
- Create `src/api/routes/speech.py` — thin API endpoints for engine status, presets, and STT request preview.
- Modify `src/api/main.py` — register speech router.
- Modify `requirements.txt` — add `httpx` only if not already present.
- Modify `.env.example` — document `SPEECH_STUDIO_BASE_URL` and timeout.
- Create `src/test_speech_presets.py` — deterministic preset/guided-option tests.
- Create `src/test_speech_studio_client.py` — mocked contract/error tests.
- Create `src/test_speech_api.py` — route-level tests for status/presets/preview.

---

### Task 1: STT preset resolver

**Files:**
- Create: `src/schemas/speech.py`
- Create: `src/services/speech_presets.py`
- Test: `src/test_speech_presets.py`

**Interfaces:**
- Produces: `SpeechSttPresetName = Literal["fast", "balanced", "max_quality"]`
- Produces: `SpeechSttOptions` Pydantic model for user-facing options.
- Produces: `ResolvedSpeechSttConfig` Pydantic model containing the raw Speech Studio parameters.
- Produces: `list_builtin_stt_presets() -> list[SpeechSttPresetSummary]`
- Produces: `resolve_stt_config(options: SpeechSttOptions) -> ResolvedSpeechSttConfig`

- [ ] **Step 1: Write failing preset tests**

Create `src/test_speech_presets.py` with tests covering:

```python
from src.schemas.speech import SpeechSttOptions
from src.services.speech_presets import resolve_stt_config


def test_fast_preset_is_lightweight():
    result = resolve_stt_config(SpeechSttOptions(preset="fast"))
    assert result.model == "small"
    assert result.compute_type == "int8"
    assert result.batch_size == 2
    assert result.no_diarization is True
    assert result.vad_onset == 0.500
    assert result.vad_offset == 0.363


def test_balanced_preset_is_default_general_mode():
    result = resolve_stt_config(SpeechSttOptions(preset="balanced", identify_speakers=True))
    assert result.model == "medium"
    assert result.compute_type == "int8"
    assert result.no_diarization is False
    assert result.batch_size in {1, 2}


def test_max_quality_prefers_safe_memory_settings():
    result = resolve_stt_config(SpeechSttOptions(preset="max_quality"))
    assert result.model == "large-v3"
    assert result.compute_type == "int8"
    assert result.batch_size == 1


def test_quiet_speech_enables_sensitive_vad():
    result = resolve_stt_config(
        SpeechSttOptions(preset="balanced", quiet_speech=True)
    )
    assert result.vad_onset == 0.1
    assert result.vad_offset == 0.1


def test_exact_speaker_count_wins_over_range():
    result = resolve_stt_config(
        SpeechSttOptions(
            preset="balanced",
            identify_speakers=True,
            num_speakers=2,
            min_speakers=1,
            max_speakers=4,
        )
    )
    assert result.num_speakers == 2
    assert result.min_speakers is None
    assert result.max_speakers is None
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
docker compose run --rm --no-deps backend sh -lc "pip install pytest && python -m pytest src/test_speech_presets.py -v"
```

Expected: collection/import failure because `src.schemas.speech` and `src.services.speech_presets` do not exist.

- [ ] **Step 3: Implement schemas and resolver**

Implement the exact user-facing fields:

```python
class SpeechSttOptions(BaseModel):
    preset: Literal["fast", "balanced", "max_quality"] = "balanced"
    language: str | None = None
    identify_speakers: bool = False
    num_speakers: int | None = Field(default=None, ge=1)
    min_speakers: int | None = Field(default=None, ge=1)
    max_speakers: int | None = Field(default=None, ge=1)
    quiet_speech: bool = False
    initial_prompt: str | None = None
```

Resolved fields must match the current Speech Studio `/stt/transcribe` contract:

```python
class ResolvedSpeechSttConfig(BaseModel):
    model: str
    language: str | None
    device: str = "auto"
    compute_type: str
    batch_size: int
    no_diarization: bool
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None
    speaker_profile: str | None = None
    formats: str = "txt json srt vtt"
    vad_onset: float
    vad_offset: float
    chunk_size: int = 30
    initial_prompt: str | None = None
```

Rules:
- `fast`: `small`, `int8`, batch `2`, diarization off unless explicitly requested.
- `balanced`: `medium`, `int8`, batch `2`, diarization on only when requested.
- `max_quality`: `large-v3`, `int8`, batch `1`, diarization on only when requested.
- `quiet_speech=True`: VAD `0.1/0.1`; otherwise Speech Studio defaults `0.500/0.363`.
- Exact `num_speakers` clears min/max.
- Validate `min_speakers <= max_speakers` when both are provided.

- [ ] **Step 4: Run preset tests to verify GREEN**

Run the same pytest command. Expected: all tests in `src/test_speech_presets.py` pass.

- [ ] **Step 5: Commit**

```bash
git add src/schemas/speech.py src/services/speech_presets.py src/test_speech_presets.py
git commit -m "feat: add user-friendly speech STT presets"
```

---

### Task 2: Speech Studio HTTP client

**Files:**
- Create: `src/services/speech_studio_client.py`
- Modify: `requirements.txt`
- Modify: `.env.example`
- Test: `src/test_speech_studio_client.py`

**Interfaces:**
- Consumes: `ResolvedSpeechSttConfig`
- Produces: `SpeechStudioClient(base_url: str | None = None, timeout_seconds: float | None = None)`
- Produces: `health() -> SpeechEngineStatus`
- Produces: `transcribe_file(file_name: str, file_bytes: bytes, config: ResolvedSpeechSttConfig) -> SpeechSttEngineResult`
- Produces normalized exceptions: `SpeechStudioOfflineError`, `SpeechStudioBusyError`, `SpeechStudioRequestError`

- [ ] **Step 1: Write failing client tests**

Mock HTTPX transport and assert:
- health success returns `online=True`.
- connection error returns/raises the normalized offline state rather than leaking HTTPX internals.
- HTTP 409 from `/stt/transcribe` becomes `SpeechStudioBusyError`.
- multipart request includes the uploaded file and resolved form fields.
- fields with `None` are omitted from the multipart form.

Use a fake `/stt/transcribe` response matching the current Speech Studio shape:

```python
{
    "success": True,
    "output_dir": "...",
    "artifacts": [],
    "stdout": "",
    "stderr": "",
    "returncode": 0,
    "logs": "",
    "error": None,
    "message": "Transcricao concluida."
}
```

- [ ] **Step 2: Run client tests to verify RED**

Run:

```powershell
docker compose run --rm --no-deps backend sh -lc "pip install pytest && python -m pytest src/test_speech_studio_client.py -v"
```

Expected: import failure because the client does not exist.

- [ ] **Step 3: Implement minimal client**

Use `httpx.Client` with:
- default base URL from `SPEECH_STUDIO_BASE_URL`, fallback `http://host.docker.internal:8010` for local Docker development;
- timeout from `SPEECH_STUDIO_TIMEOUT_SECONDS`, fallback `30` for health and explicit long timeout for transcription request construction only when used;
- no secrets in frontend-facing responses.

`health()` should call Speech Studio `/health` and normalize failures into a stable `SpeechEngineStatus` model.

`transcribe_file()` builds multipart form data from `ResolvedSpeechSttConfig.model_dump(exclude_none=True)` and converts booleans to lowercase strings accepted by FastAPI form parsing.

- [ ] **Step 4: Run client tests to verify GREEN**

Expected: all client tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/speech_studio_client.py src/test_speech_studio_client.py requirements.txt .env.example
git commit -m "feat: add Speech Studio API client"
```

---

### Task 3: Content Radar speech API foundation

**Files:**
- Create: `src/api/routes/speech.py`
- Modify: `src/api/main.py`
- Test: `src/test_speech_api.py`

**Interfaces:**
- Consumes: `list_builtin_stt_presets`, `resolve_stt_config`, `SpeechStudioClient`
- Produces: `GET /speech/status`
- Produces: `GET /speech/stt/presets`
- Produces: `POST /speech/stt/resolve`

- [ ] **Step 1: Write failing API tests**

Use FastAPI `TestClient` and dependency monkeypatching to verify:

```python
def test_stt_presets_expose_three_builtin_modes():
    response = client.get("/speech/stt/presets")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["presets"]]
    assert names == ["fast", "balanced", "max_quality"]


def test_resolve_endpoint_returns_technical_config():
    response = client.post(
        "/speech/stt/resolve",
        json={"preset": "balanced", "identify_speakers": True, "quiet_speech": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resolved"]["model"] == "medium"
    assert body["resolved"]["no_diarization"] is False
    assert body["resolved"]["vad_onset"] == 0.1
```

Status endpoint must return HTTP 200 even if the engine is unavailable; engine offline is a capability state, not a Content Radar API outage.

- [ ] **Step 2: Run API tests to verify RED**

Run:

```powershell
docker compose run --rm --no-deps backend sh -lc "pip install pytest && python -m pytest src/test_speech_api.py -v"
```

Expected: 404/import failure because speech routes are not registered.

- [ ] **Step 3: Implement thin speech routes**

Routes must contain no raw HTTPX logic. They call the service/client layer only.

Response shape:

```json
GET /speech/status
{
  "engine": "speech_studio",
  "online": false,
  "base_url": "configured",
  "message": "Speech Studio indisponível"
}
```

```json
GET /speech/stt/presets
{
  "presets": [
    {"name": "fast", "label": "Rápido", "description": "..."},
    {"name": "balanced", "label": "Equilibrado", "description": "..."},
    {"name": "max_quality", "label": "Máxima qualidade", "description": "..."}
  ]
}
```

`POST /speech/stt/resolve` returns both original user-facing options and the resolved raw configuration so the future UI can explain what will actually run.

- [ ] **Step 4: Run API tests to verify GREEN**

Expected: all speech API tests pass.

- [ ] **Step 5: Run regression suite**

Run the existing 47-test discovery suite plus speech tests:

```powershell
docker compose run --rm --no-deps backend sh -lc "pip install pytest && python -m pytest src/test_speech_presets.py src/test_speech_studio_client.py src/test_speech_api.py src/test_reference_dedup.py src/test_reference_reconciliation.py src/test_youtube_metadata.py src/test_topics.py src/test_topic_classifier.py src/test_topic_persistence.py src/test_transcript_topic_enrichment.py src/test_channel_profiles.py src/test_radar_metrics.py src/test_search_topics.py src/test_discovery_terms.py src/test_discovery_terms_freshness.py src/test_global_search.py src/test_series_detection.py src/test_radar_topics.py -v"
```

Expected: all tests pass; Pydantic deprecation warnings may remain but no failures.

- [ ] **Step 6: Commit**

```bash
git add src/api/routes/speech.py src/api/main.py src/test_speech_api.py
git commit -m "feat: expose speech engine status and STT presets"
```

---

### Task 4: Speech Studio contract gap for initial prompt

**Files:**
- Modify in Speech Studio: `api/routes_stt.py`
- Test in Speech Studio: add or extend API contract test for STT command construction.

**Interfaces:**
- Consumes: Content Radar `ResolvedSpeechSttConfig.initial_prompt`
- Produces: Speech Studio `/stt/transcribe` optional form field `initial_prompt: str | None`

- [ ] **Step 1: Write failing Speech Studio test**

Assert that posting `initial_prompt="Hades, Poseidon, DrathosSMP"` results in subprocess command arguments containing:

```text
--initial-prompt
Hades, Poseidon, DrathosSMP
```

- [ ] **Step 2: Run Speech Studio test to verify RED**

Expected: current route ignores/does not accept `initial_prompt`.

- [ ] **Step 3: Add optional form field**

In `api/routes_stt.py` add:

```python
initial_prompt: Optional[str] = Form(None),
```

and append:

```python
if initial_prompt:
    command.extend(["--initial-prompt", initial_prompt])
```

Do not alter existing defaults or STT behavior when the field is omitted.

- [ ] **Step 4: Run Speech Studio tests to verify GREEN**

Expected: new contract test passes and existing Speech Studio API tests remain green.

- [ ] **Step 5: Commit in Speech Studio repository**

```bash
git add api/routes_stt.py <test-file>
git commit -m "feat: expose STT initial prompt through API"
```

---

## Verification Gate

Before claiming this sub-project complete, verify all of the following with fresh output:

1. Content Radar speech preset tests pass.
2. Content Radar Speech Studio client tests pass.
3. Content Radar speech API tests pass.
4. Existing Content Radar regression suite still passes.
5. Existing `python -m src.test_captions` still passes against migrated DB.
6. Content Radar frontend `npm run build` still passes even though this phase adds no frontend UI.
7. Speech Studio contract test for `initial_prompt` passes.
8. Manual status smoke test with Speech Studio offline returns a graceful `online=false` response rather than breaking Content Radar.

After this foundation is verified, create a separate implementation plan for the `/audio` UI and asynchronous STT job flow. TTS/voices remain a later plan.