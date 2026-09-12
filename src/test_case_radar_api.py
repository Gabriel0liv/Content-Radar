from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.case_radar import get_case_radar_service


client = TestClient(app)


def _run(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": 1,
        "status": "queued",
        "stage": "queued",
        "progress_percent": 0,
        "progress_message": None,
        "request_json": {"theme": "casos estranhos"},
        "provider_coverage_json": {},
        "discovered_candidates": 0,
        "clustered_cases": 0,
        "usable_cases": 0,
        "rejected_cases": 0,
        "worker_id": None,
        "errors_json": [],
        "result_summary_json": None,
        "created_at": now,
        "started_at": None,
        "finished_at": None,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _case(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": 10,
        "run_id": 1,
        "provisional_title": "Caso da floresta",
        "normalized_summary": None,
        "status": "researching",
        "alleged_date": None,
        "alleged_location": None,
        "earliest_known_date": None,
        "origin_status": "unknown",
        "origin_confidence": 0.0,
        "research_confidence": 0.0,
        "likely_original_source_id": None,
        "earliest_known_source_id": None,
        "selected_primary_source_id": None,
        "dossier_version": 1,
        "dossier_json": None,
        "manual_notes": None,
        "already_used": False,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_create_case_research_run_returns_201():
    captured = {}

    class FakeService:
        def create_run(self, request):
            captured["request"] = request
            return _run(request_json=request.model_dump(mode="json"))

    app.dependency_overrides[get_case_radar_service] = lambda: FakeService()
    try:
        response = client.post(
            "/case-radar/runs",
            json={
                "theme": "vídeos estranhos na floresta",
                "desired_usable_cases": 8,
                "languages": ["pt", "en", "es"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert captured["request"].desired_usable_cases == 8
    assert response.json()["request_json"]["theme"] == "vídeos estranhos na floresta"


def test_get_missing_run_returns_404():
    class FakeService:
        def get_run(self, run_id):
            return None

    app.dependency_overrides[get_case_radar_service] = lambda: FakeService()
    try:
        response = client.get("/case-radar/runs/999")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_cancel_run_returns_cancelled_state():
    class FakeService:
        def cancel_run(self, run_id):
            return _run(id=run_id, status="cancelled", stage="cancelled")

    app.dependency_overrides[get_case_radar_service] = lambda: FakeService()
    try:
        response = client.post("/case-radar/runs/4/cancel")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == 4
    assert response.json()["status"] == "cancelled"


def test_list_runs_preserves_pagination_contract():
    captured = {}

    class FakeService:
        def list_runs(self, limit, offset):
            captured["limit"] = limit
            captured["offset"] = offset
            return [_run(id=2)], 12

    app.dependency_overrides[get_case_radar_service] = lambda: FakeService()
    try:
        response = client.get("/case-radar/runs?limit=5&offset=10")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {"limit": 5, "offset": 10}
    assert response.json()["total"] == 12
    assert response.json()["limit"] == 5
    assert response.json()["offset"] == 10


def test_patch_case_accepts_manual_curation_fields():
    captured = {}

    class FakeService:
        def update_case(self, case_id, patch):
            captured["case_id"] = case_id
            captured["patch"] = patch.model_dump(exclude_unset=True)
            return _case(id=case_id, status="approved", manual_notes="usar no vídeo")

    app.dependency_overrides[get_case_radar_service] = lambda: FakeService()
    try:
        response = client.patch(
            "/case-radar/cases/10",
            json={"status": "approved", "manual_notes": "usar no vídeo"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["patch"] == {"status": "approved", "manual_notes": "usar no vídeo"}
    assert response.json()["status"] == "approved"


def test_patch_case_rejects_automatic_confidence_fields():
    response = client.patch(
        "/case-radar/cases/10",
        json={"origin_confidence": 1.0},
    )
    assert response.status_code == 422


def test_run_children_return_404_before_listing_when_run_missing():
    class FakeService:
        def get_run(self, run_id):
            return None

    app.dependency_overrides[get_case_radar_service] = lambda: FakeService()
    try:
        responses = [
            client.get("/case-radar/runs/999/queries"),
            client.get("/case-radar/runs/999/sources"),
            client.get("/case-radar/runs/999/cases"),
        ]
    finally:
        app.dependency_overrides.clear()

    assert all(response.status_code == 404 for response in responses)
