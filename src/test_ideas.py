import src.db.base  # noqa: F401

from fastapi.testclient import TestClient

from src.api.main import app
from src.schemas.ideas import ACTIVE_IDEA_STATUSES, IdeaCreate, IdeaRead, IdeaUpdate


def test_active_api_exposes_ideas_but_not_workshop_children():
    client = TestClient(app)

    ideas = client.get("/video-projects")
    assert ideas.status_code == 200, ideas.text

    assert client.get("/video-projects/999999/items").status_code == 404
    assert client.get("/canva/oauth/start").status_code == 404
    assert client.get("/video-projects/999999/external-boards").status_code == 404


def test_active_idea_statuses_are_intentionally_small():
    assert ACTIVE_IDEA_STATUSES == {"idea", "researching", "ready", "archived"}


def test_idea_write_contract_rejects_legacy_statuses():
    IdeaCreate(title="Teste", status="idea")
    IdeaUpdate(status="researching")

    try:
        IdeaCreate(title="Teste", status="scripting")
    except ValueError:
        pass
    else:
        raise AssertionError("legacy status should not be accepted for new writes")


def test_idea_read_contract_accepts_legacy_statuses():
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    idea = IdeaRead(
        id=1,
        title="Registro antigo",
        description=None,
        niche=None,
        status="scripting",
        priority=0,
        created_at=now,
        updated_at=now,
    )
    assert idea.status == "scripting"
