# Unified Speech Suite Phase 0 + 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the temporary external Speech Studio integration with a native Content Radar speech domain, persistent PostgreSQL-backed speech jobs, and a local worker protocol that can later host WhisperX/pyannote/TTS without making the main API import heavy ML dependencies.

**Architecture:** Content Radar remains the only application and source of truth. The main FastAPI process owns validation, persistence, job orchestration, and durable transcript links; a separate `speech_worker` process in the same repository claims queued jobs from PostgreSQL using row locking and lease/heartbeat fields. Phase 0 removes the remote-service assumption; Phase 1 establishes the domain, schema, repository/service layer, worker claim loop, API contracts, and migration needed by later STT/TTS phases.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL, Alembic, pytest, existing Docker Compose stack.

**Spec:** `docs/superpowers/specs/2026-09-05-unified-speech-suite-design.md`

## Global Constraints

- Content Radar is the single repository, product, frontend, database, and daily-use workspace.
- The Speech Studio repository is not a runtime dependency.
- Do not add WhisperX, pyannote, PyTorch, CUDA, Piper, Kokoro, or other heavy speech-engine imports to the main FastAPI process in this phase.
- `speech_worker/` lives inside Content Radar but remains a separate process boundary.
- PostgreSQL is the only queue/state dependency in Phase 1; do not add Redis or Celery.
- One heavy job at a time per worker initially; schema must support multiple workers later.
- Main API/service layer remains the durable-data owner.
- Worker execution state must survive API restarts and support stale-lease recovery.
- Existing Radar, Pesquisas, Biblioteca, Ideias, reference imports, transcript versioning, and the current 61-test regression set must continue to work.
- Built-in STT presets `fast`, `balanced`, and `max_quality` remain reusable, but must no longer depend on a remote `SPEECH_STUDIO_BASE_URL` client.
- All worker-facing paths must be managed server-generated paths under the configured speech data root; arbitrary user paths are forbidden.

---

## File map locked for this phase

### Remove remote integration assumptions

- Delete: `src/services/speech_studio_client.py`
- Modify: `.env.example`
- Modify: `src/api/routes/speech.py`
- Modify: `src/test_speech_studio_client.py` (delete after equivalent native tests exist)
- Modify: `src/test_speech_api.py`

### New speech domain

- Create: `src/models/speech.py`
- Create: `src/schemas/speech_jobs.py`
- Create: `src/repositories/speech_jobs.py`
- Create: `src/services/speech_jobs_service.py`
- Create: `src/services/speech_storage.py`
- Create: `src/services/speech_worker_protocol.py`
- Create: `src/api/routes/speech_jobs.py`

### Worker foundation

- Create: `speech_worker/__init__.py`
- Create: `speech_worker/worker.py`
- Create: `speech_worker/runtime/__init__.py`
- Create: `speech_worker/runtime/capabilities.py`
- Create: `speech_worker/runtime/executor.py`

### Database/migrations

- Create: `alembic/versions/0019_add_speech_job_foundation.py`
- Modify: `src/api/main.py`
- Modify: model import/bootstrap locations as required by the current SQLAlchemy metadata-loading pattern.

### Tests

- Create: `src/test_speech_job_models.py`
- Create: `src/test_speech_job_repository.py`
- Create: `src/test_speech_jobs_service.py`
- Create: `src/test_speech_worker_protocol.py`
- Create: `src/test_speech_storage.py`
- Modify: `src/test_speech_presets.py`
- Modify: `src/test_speech_api.py`

---

### Task 1: Remove the remote Speech Studio runtime contract

**Files:**
- Delete: `src/services/speech_studio_client.py`
- Modify: `.env.example`
- Modify: `src/api/routes/speech.py`
- Modify: `src/test_speech_api.py`
- Delete: `src/test_speech_studio_client.py`

**Interfaces:**
- Consumes: existing `list_builtin_stt_presets()` and `resolve_stt_config()` from `src/services/speech_presets.py`.
- Produces: a speech route module that exposes only native preset/config-resolution endpoints in this task. Job/status endpoints come in later tasks.

- [ ] **Step 1: Rewrite the API test so no remote client is referenced**

Keep tests for built-in presets and resolver, and replace remote-health expectations with a temporary native foundation response contract:

```python
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_stt_presets_expose_three_builtin_modes():
    response = client.get("/speech/stt/presets")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["presets"]]
    assert ids == ["fast", "balanced", "max_quality"]


def test_resolve_endpoint_returns_technical_config():
    response = client.post(
        "/speech/stt/resolve",
        json={"preset": "balanced", "diarization": True, "num_speakers": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "medium"
    assert payload["num_speakers"] == 2
    assert payload["no_diarization"] is False
```

- [ ] **Step 2: Run the targeted API tests before deletion**

Run:

```powershell
python -m pytest src/test_speech_api.py -v
```

Expected: current resolver/preset tests pass; any test importing `SpeechStudioClient` must still exist and therefore identify what needs removal.

- [ ] **Step 3: Remove remote-client imports and status endpoint from `src/api/routes/speech.py`**

The module at the end of this task must contain only resolver/preset behavior, conceptually:

```python
router = APIRouter(prefix="/speech", tags=["Speech"])

@router.get("/stt/presets")
def get_stt_presets():
    return {"presets": list_builtin_stt_presets()}

@router.post("/stt/resolve", response_model=ResolvedSttConfig)
def resolve_stt(request: ResolveSttRequest):
    return resolve_stt_config(request)
```

Do not keep `/speech/status` backed by an HTTP request to another repository.

- [ ] **Step 4: Remove remote environment settings**

Delete from `.env.example`:

```env
SPEECH_STUDIO_BASE_URL=
SPEECH_STUDIO_TIMEOUT_SECONDS=
```

Add native storage/worker settings instead:

```env
SPEECH_DATA_ROOT=data/speech
SPEECH_WORKER_ID=local-worker-1
SPEECH_WORKER_POLL_SECONDS=2
SPEECH_WORKER_LEASE_SECONDS=120
SPEECH_WORKER_HEARTBEAT_SECONDS=30
```

- [ ] **Step 5: Delete `src/services/speech_studio_client.py` and `src/test_speech_studio_client.py`**

No replacement network client is created.

- [ ] **Step 6: Run the remaining speech foundation tests**

Run:

```powershell
python -m pytest src/test_speech_presets.py src/test_speech_api.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .env.example src/api/routes/speech.py src/test_speech_api.py src/services/speech_studio_client.py src/test_speech_studio_client.py
git commit -m "refactor: remove external speech studio runtime dependency"
```

---

### Task 2: Add persistent speech job and preset models

**Files:**
- Create: `src/models/speech.py`
- Create: `src/test_speech_job_models.py`

**Interfaces:**
- Produces SQLAlchemy models:
  - `SpeechJob`
  - `SpeechPreset`
  - `SpeechArtifact`
  - `SpeechSpeakerMapping`
- Later repository/service tasks depend on these exact class names and columns.

- [ ] **Step 1: Write model-shape tests**

Create tests that assert table names, required columns, and status/operation constraints without requiring a live DB:

```python
from src.models.speech import SpeechArtifact, SpeechJob, SpeechPreset, SpeechSpeakerMapping


def test_speech_job_exposes_queue_and_lease_fields():
    columns = SpeechJob.__table__.columns
    for name in (
        "operation", "status", "stage", "progress_percent",
        "requested_config_json", "resolved_config_json",
        "worker_id", "lease_expires_at", "heartbeat_at",
        "cancel_requested_at", "result_json", "error_code", "error_message",
    ):
        assert name in columns


def test_speech_preset_exposes_native_config_storage():
    columns = SpeechPreset.__table__.columns
    assert "operation" in columns
    assert "config_json" in columns
    assert "is_builtin" in columns


def test_speech_artifact_links_to_job():
    assert "speech_job_id" in SpeechArtifact.__table__.columns


def test_speaker_mapping_preserves_raw_label_separately():
    columns = SpeechSpeakerMapping.__table__.columns
    assert "raw_speaker" in columns
    assert "display_name" in columns
```

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest src/test_speech_job_models.py -v
```

Expected: FAIL because `src.models.speech` does not exist.

- [ ] **Step 3: Implement `src/models/speech.py`**

Use these semantics exactly:

```python
class SpeechJob(Base):
    __tablename__ = "speech_jobs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    operation = Column(Text, nullable=False)  # stt | tts
    status = Column(Text, nullable=False, server_default="queued")
    stage = Column(Text, nullable=False, server_default="queued")
    progress_percent = Column(Integer, nullable=False, server_default="0")
    progress_message = Column(Text, nullable=True)
    requested_config_json = Column(JSONB, nullable=False, server_default="{}")
    resolved_config_json = Column(JSONB, nullable=True)
    input_path = Column(Text, nullable=True)
    reference_source_id = Column(BigInteger, ForeignKey("reference_sources.id", ondelete="SET NULL"), nullable=True)
    transcript_id = Column(BigInteger, ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True)
    worker_id = Column(Text, nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    cancel_requested_at = Column(DateTime(timezone=True), nullable=True)
    result_json = Column(JSONB, nullable=True)
    error_code = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    debug_log_path = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

Constraints:

```python
CheckConstraint("operation IN ('stt','tts')", name="check_speech_jobs_operation")
CheckConstraint("status IN ('queued','running','completed','failed','cancelled')", name="check_speech_jobs_status")
CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="check_speech_jobs_progress")
```

`SpeechPreset`:

```python
id, name, operation, description, config_json, is_builtin, created_at, updated_at
```

with unique `(operation, name)` and operation constraint `stt|tts`.

`SpeechArtifact`:

```python
id, speech_job_id, artifact_type, storage_key, filename, mime_type, size_bytes, created_at
```

`SpeechSpeakerMapping`:

```python
id, transcript_id, speech_job_id, raw_speaker, display_name, created_at, updated_at
```

with unique `(transcript_id, raw_speaker)` when transcript is present.

- [ ] **Step 4: Run model tests**

```powershell
python -m pytest src/test_speech_job_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/models/speech.py src/test_speech_job_models.py
git commit -m "feat: add native speech domain models"
```

---

### Task 3: Add Alembic migration 0019 for speech foundation

**Files:**
- Create: `alembic/versions/0019_add_speech_job_foundation.py`

**Interfaces:**
- Consumes tables from Task 2.
- Produces DB schema required by Tasks 4-7.

- [ ] **Step 1: Create migration with exact revision chain**

Header:

```python
revision = "0019_speech_job_foundation"
down_revision = "0018_discovery_terms"
branch_labels = None
depends_on = None
```

Create `speech_jobs`, `speech_presets`, `speech_artifacts`, `speech_speaker_mappings` matching Task 2 exactly.

Indexes required:

```text
idx_speech_jobs_status_created_at
idx_speech_jobs_operation_status
idx_speech_jobs_worker_id
idx_speech_jobs_lease_expires_at
idx_speech_jobs_reference_source_id
idx_speech_artifacts_job_id
idx_speech_speaker_mappings_transcript_id
```

- [ ] **Step 2: Ensure downgrade drops dependent tables in safe order**

Order:

```text
speech_speaker_mappings
speech_artifacts
speech_presets
speech_jobs
```

- [ ] **Step 3: Validate migration head locally**

Run:

```powershell
docker compose build migrate
docker compose run --rm migrate alembic heads
```

Expected:

```text
0019_speech_job_foundation (head)
```

- [ ] **Step 4: Apply migration**

```powershell
docker compose run --rm migrate alembic upgrade head
docker compose run --rm migrate alembic current
```

Expected current revision: `0019_speech_job_foundation (head)`.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/0019_add_speech_job_foundation.py
git commit -m "feat: add speech job foundation migration"
```

---

### Task 4: Add managed speech storage service

**Files:**
- Create: `src/services/speech_storage.py`
- Create: `src/test_speech_storage.py`

**Interfaces:**
- Produces:
  - `SpeechStorage(root: Path | str)`
  - `save_input(job_id: int, filename: str, chunks: Iterable[bytes]) -> Path`
  - `job_dir(job_id: int) -> Path`
  - `artifact_path(job_id: int, filename: str) -> Path`
  - `safe_storage_key(path: Path) -> str`
- Later jobs/service code stores only paths created through this service.

- [ ] **Step 1: Write path-safety tests**

```python
from pathlib import Path
import pytest
from src.services.speech_storage import SpeechStorage


def test_job_dir_is_scoped_under_root(tmp_path):
    storage = SpeechStorage(tmp_path)
    path = storage.job_dir(42)
    assert path == tmp_path / "jobs" / "42"


def test_artifact_filename_cannot_escape_job_dir(tmp_path):
    storage = SpeechStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.artifact_path(1, "../../secret.txt")


def test_safe_storage_key_is_relative_to_root(tmp_path):
    storage = SpeechStorage(tmp_path)
    path = storage.artifact_path(3, "result.srt")
    assert storage.safe_storage_key(path) == "jobs/3/artifacts/result.srt"
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest src/test_speech_storage.py -v
```

Expected: module missing.

- [ ] **Step 3: Implement managed paths**

Layout:

```text
<root>/
  inputs/
  jobs/<job_id>/
    input/
    work/
    artifacts/
    logs/
  voices/
```

Reject filenames when `Path(filename).name != filename`, filename is empty, or contains `/` or `\\`.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest src/test_speech_storage.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/speech_storage.py src/test_speech_storage.py
git commit -m "feat: add managed speech storage"
```

---

### Task 5: Implement PostgreSQL queue repository with atomic claim and lease recovery

**Files:**
- Create: `src/repositories/speech_jobs.py`
- Create: `src/test_speech_job_repository.py`

**Interfaces:**
- Produces `SpeechJobRepository` methods:
  - `create(operation, requested_config_json, input_path=None, reference_source_id=None) -> SpeechJob`
  - `get(job_id) -> SpeechJob | None`
  - `list_recent(limit=50) -> list[SpeechJob]`
  - `request_cancel(job_id) -> SpeechJob | None`
  - `claim_next(worker_id, lease_seconds, operations=("stt","tts")) -> SpeechJob | None`
  - `heartbeat(job_id, worker_id, lease_seconds, stage=None, progress_percent=None, progress_message=None) -> SpeechJob`
  - `complete(job_id, worker_id, result_json) -> SpeechJob`
  - `fail(job_id, worker_id, error_code, error_message) -> SpeechJob`
  - `recover_stale_leases(now=None) -> int`

- [ ] **Step 1: Write repository behavior tests against a transaction-scoped PostgreSQL DB fixture**

Required scenarios:

```python
def test_claim_next_marks_job_running_and_sets_lease(...): ...
def test_second_worker_cannot_claim_same_job(...): ...
def test_heartbeat_extends_owned_lease(...): ...
def test_wrong_worker_cannot_complete_job(...): ...
def test_recover_stale_running_job_requeues_it(...): ...
def test_cancel_queued_job_becomes_cancelled(...): ...
def test_cancel_running_job_sets_cancel_requested_at(...): ...
```

Atomic claim must be implemented with PostgreSQL row locking equivalent to:

```sql
SELECT id
FROM speech_jobs
WHERE status = 'queued'
  AND operation IN (...)
ORDER BY created_at, id
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest src/test_speech_job_repository.py -v
```

Expected: repository missing.

- [ ] **Step 3: Implement repository using SQLAlchemy transaction semantics**

`claim_next()` must set in the same transaction:

```text
status=running
stage=starting
worker_id=<worker_id>
started_at=now if null
heartbeat_at=now
lease_expires_at=now + lease_seconds
```

`recover_stale_leases()` rules:

- running + expired lease + no cancel request -> queued, clear worker/lease/heartbeat, stage=`queued`, progress retained;
- running + expired lease + cancel requested -> cancelled, finished_at=now, clear lease;
- completed/failed/cancelled are untouched.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest src/test_speech_job_repository.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/repositories/speech_jobs.py src/test_speech_job_repository.py
git commit -m "feat: add postgres speech job queue repository"
```

---

### Task 6: Add speech job service and native API

**Files:**
- Create: `src/schemas/speech_jobs.py`
- Create: `src/services/speech_jobs_service.py`
- Create: `src/api/routes/speech_jobs.py`
- Modify: `src/api/main.py`
- Modify: `src/test_speech_api.py`
- Create: `src/test_speech_jobs_service.py`

**Interfaces:**
- Produces service methods:
  - `create_stt_job(...)`
  - `get_job(job_id)`
  - `list_jobs(limit=50)`
  - `cancel_job(job_id)`
- Produces API endpoints:
  - `POST /speech/jobs/stt`
  - `GET /speech/jobs`
  - `GET /speech/jobs/{job_id}`
  - `POST /speech/jobs/{job_id}/cancel`
  - existing `GET /speech/stt/presets`
  - existing `POST /speech/stt/resolve`

- [ ] **Step 1: Define Pydantic schemas**

Minimum request:

```python
class SpeechSttJobCreate(BaseModel):
    preset: Literal["fast", "balanced", "max_quality"] = "balanced"
    language: str | None = None
    diarization: bool = False
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None
    quiet_speech: bool = False
    initial_prompt: str | None = None
    reference_source_id: int | None = None
```

Read schema must expose:

```text
id, operation, status, stage, progress_percent, progress_message,
requested_config_json, resolved_config_json, reference_source_id,
transcript_id, worker_id, error_code, error_message,
created_at, started_at, finished_at, updated_at
```

- [ ] **Step 2: Write service tests**

Required:

```python
def test_create_stt_job_resolves_preset_before_persisting(...): ...
def test_create_stt_job_rejects_unknown_reference(...): ...
def test_cancel_missing_job_returns_none(...): ...
```

`create_stt_job()` must persist both user intent (`requested_config_json`) and technical config (`resolved_config_json`).

- [ ] **Step 3: Run service tests RED**

```powershell
python -m pytest src/test_speech_jobs_service.py -v
```

- [ ] **Step 4: Implement service**

Use `resolve_stt_config()` from the existing preset resolver. Do not call any speech engine in request handling.

- [ ] **Step 5: Extend API tests**

Use dependency/session overrides matching existing project test patterns. Verify:

```python
def test_create_stt_job_returns_queued_job(...):
    response = client.post("/speech/jobs/stt", json={"preset": "fast"})
    assert response.status_code == 201
    assert response.json()["status"] == "queued"


def test_cancel_queued_job(...):
    ...
```

- [ ] **Step 6: Register router in `src/api/main.py`**

```python
from src.api.routes import speech_jobs
app.include_router(speech_jobs.router, prefix="/speech", tags=["Speech Jobs"])
```

Avoid duplicate route definitions between `speech.py` and `speech_jobs.py`.

- [ ] **Step 7: Run service/API GREEN**

```powershell
python -m pytest src/test_speech_presets.py src/test_speech_jobs_service.py src/test_speech_api.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/schemas/speech_jobs.py src/services/speech_jobs_service.py src/api/routes/speech_jobs.py src/api/main.py src/test_speech_jobs_service.py src/test_speech_api.py
git commit -m "feat: add native speech jobs api"
```

---

### Task 7: Define worker protocol and non-ML worker loop

**Files:**
- Create: `src/services/speech_worker_protocol.py`
- Create: `src/test_speech_worker_protocol.py`
- Create: `speech_worker/__init__.py`
- Create: `speech_worker/runtime/__init__.py`
- Create: `speech_worker/runtime/capabilities.py`
- Create: `speech_worker/runtime/executor.py`
- Create: `speech_worker/worker.py`

**Interfaces:**
- `WorkerCapabilities` dataclass/Pydantic model with:
  - `worker_id`
  - `operations`
  - `cpu_available`
  - `cuda_available`
  - `gpu_name`
  - `vram_mb`
  - `stt_ready`
  - `diarization_ready`
  - `tts_engines`
- `SpeechExecutor.execute(job, progress_callback, cancel_check) -> dict`
- Phase 1 executor intentionally supports a deterministic `noop_test` path only in tests; real STT/TTS arrives in later phases.

- [ ] **Step 1: Write protocol tests**

Required:

```python
def test_capability_payload_has_stable_shape(): ...
def test_worker_heartbeat_progress_is_clamped_0_100(): ...
def test_worker_stops_execution_when_cancel_requested(): ...
def test_executor_rejects_unsupported_operation(): ...
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest src/test_speech_worker_protocol.py -v
```

- [ ] **Step 3: Implement lightweight capability detection without ML imports**

Phase 1 rules:

```text
cpu_available = True
cuda_available = False unless detectable without importing torch
stt_ready = False
diarization_ready = False
tts_engines = []
```

Use only stdlib/platform/subprocess-safe checks in this phase. Heavy capability probing is added with the engines later.

- [ ] **Step 4: Implement worker loop**

`worker.py` sequence:

```python
while True:
    repo.recover_stale_leases()
    job = repo.claim_next(worker_id, lease_seconds, operations=capabilities.operations)
    if job is None:
        sleep(poll_seconds)
        continue
    try:
        result = executor.execute(
            job,
            progress_callback=lambda stage, pct, msg: repo.heartbeat(...),
            cancel_check=lambda: repo.get(job.id).cancel_requested_at is not None,
        )
        repo.complete(job.id, worker_id, result)
    except JobCancelled:
        repo.mark_cancelled(job.id, worker_id)
    except UnsupportedOperationError as exc:
        repo.fail(job.id, worker_id, "unsupported_operation", str(exc))
    except Exception as exc:
        repo.fail(job.id, worker_id, "worker_error", str(exc))
```

The loop itself must be factored so one iteration can be unit-tested without an infinite loop, e.g. `run_once(...) -> bool`.

- [ ] **Step 5: Run GREEN**

```powershell
python -m pytest src/test_speech_worker_protocol.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/services/speech_worker_protocol.py src/test_speech_worker_protocol.py speech_worker
git commit -m "feat: add native speech worker protocol"
```

---

### Task 8: Add worker/status capability endpoint and Docker service skeleton

**Files:**
- Modify: `src/api/routes/speech_jobs.py`
- Modify: `docker-compose.yml`
- Create or modify: worker Dockerfile only if the existing Dockerfile cannot safely host the lightweight Phase 1 worker.
- Modify: `src/test_speech_api.py`

**Interfaces:**
- Produces `GET /speech/status` backed by native DB/worker state, not an external HTTP service.

- [ ] **Step 1: Add API test for native status**

Expected payload shape:

```json
{
  "mode": "native",
  "queue": {"queued": 0, "running": 0},
  "worker": {
    "online": false,
    "worker_id": null,
    "last_heartbeat_at": null
  }
}
```

Worker is considered online when a recent heartbeat/capability record exists within the configured stale threshold. If no worker has started yet, endpoint still returns 200.

- [ ] **Step 2: Add minimal worker presence persistence**

If the spec's `speech_jobs` rows alone cannot represent an idle worker, add a compact `speech_worker_state` table in migration 0019 before applying it, with one row per worker:

```text
worker_id (PK)
capabilities_json
last_heartbeat_at
started_at
updated_at
```

If migration 0019 has already been applied in a shared environment, create `0020_add_speech_worker_state.py` instead. Never rewrite an applied migration in a shared DB.

- [ ] **Step 3: Add worker service to Compose**

Service semantics:

```yaml
speech_worker:
  build: .
  command: python -m speech_worker.worker
  environment:
    DATABASE_URL: postgresql://radar:radar@postgres:5432/dark_content_radar
    SPEECH_DATA_ROOT: /app/data/speech
    SPEECH_WORKER_ID: local-worker-1
  volumes:
    - ./data:/app/data
  depends_on:
    postgres:
      condition: service_healthy
```

Do not add GPU runtime configuration or heavy requirements yet. That belongs to engine migration phases.

- [ ] **Step 4: Run API tests**

```powershell
python -m pytest src/test_speech_api.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml src/api/routes/speech_jobs.py src/test_speech_api.py alembic/versions src/models/speech.py speech_worker
 git commit -m "feat: wire native speech worker service"
```

---

### Task 9: Phase 0 + 1 verification gate

**Files:** no feature edits unless verification exposes a defect.

**Interfaces:** This task certifies the foundation required by Phase 2.

- [ ] **Step 1: Build backend and migration images**

```powershell
docker compose build backend migrate speech_worker
```

Expected: all requested images build successfully.

- [ ] **Step 2: Verify migration head/current**

```powershell
docker compose run --rm migrate alembic heads
docker compose run --rm migrate alembic current
```

Expected: current equals latest speech migration head.

- [ ] **Step 3: Run new speech tests**

```powershell
docker compose run --rm --no-deps backend sh -lc "pip install pytest && python -m pytest \
src/test_speech_presets.py \
src/test_speech_job_models.py \
src/test_speech_storage.py \
src/test_speech_job_repository.py \
src/test_speech_jobs_service.py \
src/test_speech_worker_protocol.py \
src/test_speech_api.py -v"
```

Expected: all pass.

- [ ] **Step 4: Run existing regression suite**

```powershell
docker compose run --rm --no-deps backend sh -lc "pip install pytest && python -m pytest \
src/test_reference_dedup.py \
src/test_reference_reconciliation.py \
src/test_youtube_metadata.py \
src/test_topics.py \
src/test_topic_classifier.py \
src/test_topic_persistence.py \
src/test_transcript_topic_enrichment.py \
src/test_channel_profiles.py \
src/test_radar_metrics.py \
src/test_search_topics.py \
src/test_discovery_terms.py \
src/test_discovery_terms_freshness.py \
src/test_global_search.py \
src/test_series_detection.py \
src/test_radar_topics.py \
src/test_captions.py -v"
```

Expected: all pass. Existing Pydantic deprecation warnings do not fail this gate.

- [ ] **Step 5: Start stack and inspect status**

```powershell
docker compose up -d --build
Invoke-RestMethod http://localhost:8000/speech/status
```

Expected:

```text
mode = native
worker.online = true
```

The Phase 1 worker may report `stt_ready=false` and `tts_engines=[]`; that is correct until engine migration.

- [ ] **Step 6: Queue a placeholder STT job only if the API explicitly marks unsupported execution**

The foundation must not pretend transcription works yet. A queued STT job claimed by a Phase 1 worker must fail deterministically with:

```text
error_code = unsupported_operation
```

or remain queued if worker capabilities exclude `stt`. Prefer the latter: worker only claims operations it reports ready for. This verifies capability-aware claiming without fake success.

- [ ] **Step 7: Record verification result in the next phase handoff**

Phase 2 must not begin until:

```text
- migration applied
- native status endpoint works
- stale lease recovery tested
- cancellation tested
- worker can idle safely
- old SpeechStudioClient is gone
- regression suite remains green
```

---

## Self-review against the spec

Coverage in this plan:

- external Speech Studio runtime dependency removal: Task 1;
- one authoritative PostgreSQL speech domain: Tasks 2-6;
- PostgreSQL queue without Redis/Celery: Task 5;
- one-heavy-job-per-worker compatible protocol: Tasks 5 and 7;
- lease/heartbeat/recovery/cancellation: Tasks 5, 7, 8;
- managed safe storage foundation: Task 4;
- native presets and resolved config: Tasks 1 and 6;
- API remains free of heavy ML imports: Tasks 1-8;
- same-repo worker boundary: Tasks 7-8;
- graceful status when worker unavailable: Task 8;
- existing Content Radar regression safety: Task 9.

Explicitly deferred to later plans, as required by the approved phased SDD:

- WhisperX/pyannote migration and real STT execution: Phase 2;
- Audio Next.js UI: Phase 3;
- Library/reference STT orchestration and transcript normalization: Phase 4;
- Piper/Kokoro/TTS migration: Phase 5;
- voices/personal preset UX/history polish: Phase 6;
- archiving the old Speech Studio repository: Phase 7.

No Redis/Celery, no external Speech Studio URL/client, no heavy speech dependency is introduced by this plan.
