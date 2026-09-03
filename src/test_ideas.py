import src.db.base  # noqa: F401

from src.api.main import app
from src.schemas.ideas import ACTIVE_IDEA_STATUSES, IdeaCreate, IdeaRead, IdeaUpdate


def test_active_api_exposes_ideas_but_not_workshop_children():
    paths = {route.path for route in app.routes}
    assert "/video-projects" in paths
    assert "/video-projects/{id}" in paths
    assert "/video-projects/{id}/items" not in paths
    assert "/canva/oauth/start" not in paths
    assert "/video-projects/{id}/external-boards" not in paths


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
