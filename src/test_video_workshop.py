import sys
import time
import hashlib
import base64
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import src.db.base
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from src.api.main import app
from src.db.session import Base
from src.db.session import SessionLocal
from src.models.canva_oauth import CanvaOAuthState, CanvaOAuthToken
from src.models.video_workshop import (
    VideoProject,
    VideoProjectAudioIdea,
    VideoProjectExternalBoard,
    VideoProjectItem,
    VideoProjectNote,
    VideoProjectReference,
)
from src.schemas.video_workshop import (
    VideoProjectAudioIdeaCreate,
    VideoProjectCreate,
    VideoProjectItemCreate,
    VideoProjectItemFromScriptExcerpt,
    VideoProjectNoteCreate,
    VideoProjectReferenceCreate,
    VideoProjectUpdate,
)
from src.schemas.canva_oauth import CanvaOAuthStatusRead
from src.services.canva_oauth_service import CanvaOAuthService
from src.services.external_boards_service import ExternalBoardsService
from src.services.video_workshop_service import (
    VideoWorkshopService,
    calculate_word_and_duration,
    extract_text_from_tiptap_json,
)


class MockHTTPResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str | None = None):
        self._payload = payload
        self.status_code = status_code
        self.text = text or ""
        self.content = b"payload"

    def json(self):
        return self._payload


def reset_canva_oauth_tables(db):
    Base.metadata.create_all(bind=db.get_bind(), tables=[CanvaOAuthState.__table__, CanvaOAuthToken.__table__])
    db.query(CanvaOAuthState).delete()
    db.query(CanvaOAuthToken).delete()
    db.commit()


def create_mock_canva_board(
    service: ExternalBoardsService,
    project_id: int,
    external_id: str = "canva-design-123",
) -> VideoProjectExternalBoard:
    project = service._get_project(project_id)
    assert project is not None, "Projeto de vídeo não encontrado para mock do Canva"

    board = VideoProjectExternalBoard(
        video_project_id=project_id,
        provider="canva",
        external_id=external_id,
        title=f"{project.title} - Canva",
        view_url=f"https://www.canva.com/design/{external_id}/view?token=temp-view",
        edit_url=f"https://www.canva.com/design/{external_id}/edit?token=temp-edit",
        metadata_json={
            "mocked_provider": True,
            "blank_design": True,
            "temporary_links": True,
        },
    )
    service.db.add(board)
    service.db.commit()
    service.db.refresh(board)
    service._touch_project(project)
    return board


def test_tiptap_word_count():
    print("Running test_tiptap_word_count...")

    tiptap_json = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Este é um teste do editor."}
                ],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Outro parágrafo com mais palavras."}
                ],
            },
        ],
    }
    extracted_text = extract_text_from_tiptap_json(tiptap_json)
    assert extracted_text == "Este é um teste do editor. Outro parágrafo com mais palavras.", f"Got '{extracted_text}'"

    word_count, duration = calculate_word_and_duration(extracted_text)
    assert word_count == 11, f"Expected 11 words, got {word_count}"
    assert duration == 4, f"Expected 4 seconds, got {duration}"
    print("✓ Tiptap text parser and word count passed")


def test_video_projects_crud_and_cascade():
    print("\nRunning test_video_projects_crud_and_cascade (DB integration)...")
    db = SessionLocal()
    workshop_service = VideoWorkshopService(db)
    external_boards_service = ExternalBoardsService(db)

    project_payload = VideoProjectCreate(
        title="Novo Vídeo do Canal",
        working_title="Como programar em Python",
        description="Um tutorial prático de Python para iniciantes",
        niche="Tecnologia",
        target_platform="YouTube",
        video_format="Video Normal",
        target_duration_seconds=600,
        status="idea",
        priority=3,
    )
    project = workshop_service.create_video_project(project_payload)
    project_id = project.id
    print(f"Created video project: ID={project_id}, title='{project.title}'")
    assert project.status == "idea"
    assert project.word_count == 0
    assert project.estimated_duration_seconds is None or project.estimated_duration_seconds == 0

    try:
        updated_project = workshop_service.update_video_project(
            project_id,
            VideoProjectUpdate(
                script_text="Olá pessoal, hoje vamos aprender a programar em Python do zero absoluta. O Python é fantástico."
            ),
        )
        print(
            f"Updated script: word_count={updated_project.word_count}, "
            f"estimated_duration={updated_project.estimated_duration_seconds}"
        )
        assert updated_project.word_count == 16
        assert updated_project.estimated_duration_seconds == 6

        note = workshop_service.create_note_for_project(
            project_id,
            VideoProjectNoteCreate(
                note_type="idea",
                title="Gancho inicial",
                body="Começar com uma pergunta instigante sobre o mercado de programação.",
                pinned=True,
            ),
        )
        print(f"Created note: ID={note.id}, type={note.note_type}, pinned={note.pinned}")
        assert note.pinned is True

        ref = workshop_service.create_reference_for_project(
            project_id,
            VideoProjectReferenceCreate(
                external_url="https://docs.python.org",
                title="Documentação Oficial",
                note="Ótimo link para colocar na descrição",
            ),
        )
        print(f"Created reference: ID={ref.id}, title='{ref.title}'")

        audio = workshop_service.create_audio_idea_for_project(
            project_id,
            VideoProjectAudioIdeaCreate(
                audio_title="Upbeat Tech Music",
                audio_url="https://example.com/audio.mp3",
                audio_type="background_music",
                mood="energetic",
            ),
        )
        print(f"Created audio idea: ID={audio.id}, mood='{audio.mood}'")

        note_item = workshop_service.create_item_for_project(
            project_id,
            VideoProjectItemCreate(
                item_type="note",
                title="Gancho em cartão",
                body="Abrir com uma dor clara do público.",
                pinned=True,
            ),
        )
        reference_item = workshop_service.create_item_for_project(
            project_id,
            VideoProjectItemCreate(
                item_type="reference",
                title="Python Docs",
                url="https://docs.python.org",
                body="Usar como apoio factual.",
            ),
        )
        script_item = workshop_service.create_item_from_script_excerpt(
            project_id,
            VideoProjectItemFromScriptExcerpt(
                text="Hoje vamos mostrar o caminho mais curto para sair do zero em Python.",
                title="Trecho de roteiro",
            ),
        )
        canva_board = create_mock_canva_board(external_boards_service, project_id)
        print(
            f"Created unified items: note_item={note_item.id}, reference_item={reference_item.id}, "
            f"script_item={script_item.id}, canva_board={canva_board.id}"
        )

        try:
            workshop_service.update_video_project(project_id, VideoProjectUpdate(status="invalid_status_value"))
            assert False, "Expected CheckConstraint error for invalid status"
        except IntegrityError:
            db.rollback()
            print("✓ Check constraint on status rejected invalid value successfully")

        success = workshop_service.delete_video_project(project_id)
        assert success is True
        print(f"Deleted project: ID={project_id}")

        notes = db.query(VideoProjectNote).filter(VideoProjectNote.video_project_id == project_id).all()
        assert len(notes) == 0, f"Expected notes to be cascading deleted, got {len(notes)}"

        refs = db.query(VideoProjectReference).filter(VideoProjectReference.video_project_id == project_id).all()
        assert len(refs) == 0, f"Expected references to be cascading deleted, got {len(refs)}"

        audios = db.query(VideoProjectAudioIdea).filter(VideoProjectAudioIdea.video_project_id == project_id).all()
        assert len(audios) == 0, "Expected audio ideas to be cascading deleted"

        items = db.query(VideoProjectItem).filter(VideoProjectItem.video_project_id == project_id).all()
        assert len(items) == 0, f"Expected unified items to be cascading deleted, got {len(items)}"

        boards = db.query(VideoProjectExternalBoard).filter(
            VideoProjectExternalBoard.video_project_id == project_id
        ).all()
        assert len(boards) == 0, f"Expected external boards to be cascading deleted, got {len(boards)}"

        print("✓ Cascade deletes verified successfully")

    finally:
        db.query(VideoProject).filter(VideoProject.id == project_id).delete()
        db.commit()
        db.close()

    print("✓ test_video_projects_crud_and_cascade passed")


def test_items_script_excerpt_and_mocked_canva_external_board():
    print("\nRunning test_items_script_excerpt_and_mocked_canva_external_board...")
    db = SessionLocal()
    workshop_service = VideoWorkshopService(db)
    external_boards_service = ExternalBoardsService(db)

    project = workshop_service.create_video_project(
        VideoProjectCreate(title="External Canva Test", status="idea", priority=0)
    )
    project_id = project.id
    original_updated_at = project.updated_at

    try:
        updated_project = workshop_service.update_video_project(
            project_id,
            VideoProjectUpdate(
                script_text=(
                    "Gancho forte. Promessa clara. Passo a passo enxuto. "
                    "Fechamento com CTA direto."
                )
            ),
        )
        assert updated_project.word_count == 12
        assert updated_project.estimated_duration_seconds == 5

        item_ids = []
        for payload in [
            VideoProjectItemCreate(item_type="note", title="Hook", body="Abrir com uma tensão.", pinned=True),
            VideoProjectItemCreate(item_type="todo", title="CTA", body="Fechar com próxima ação."),
            VideoProjectItemCreate(item_type="reference", title="Fonte", url="https://example.com/fonte"),
        ]:
            item = workshop_service.create_item_for_project(project_id, payload)
            item_ids.append(item.id)

        excerpt_item = workshop_service.create_item_from_script_excerpt(
            project_id,
            VideoProjectItemFromScriptExcerpt(
                text="Promessa clara em até oito segundos.",
                title="Bloco do roteiro",
            ),
        )
        item_ids.append(excerpt_item.id)

        ordered_items = workshop_service.list_items_for_project(project_id)
        assert len(ordered_items) == 4, f"Expected 4 unified items, got {len(ordered_items)}"
        assert ordered_items[0].pinned is True, "Pinned item should be listed first"
        assert any(item.item_type == "script_excerpt" for item in ordered_items)

        time.sleep(0.1)
        canva_board = create_mock_canva_board(external_boards_service, project_id, external_id="design-temp-456")
        listed_boards = external_boards_service.get_external_boards_for_project(project_id)
        assert len(listed_boards) == 1, f"Expected 1 external board, got {len(listed_boards)}"
        assert listed_boards[0].provider == "canva"
        assert listed_boards[0].metadata_json["mocked_provider"] is True
        assert "temp-" in listed_boards[0].view_url

        db.expire_all()
        refreshed_project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
        assert refreshed_project.updated_at > original_updated_at, "External board should touch project.updated_at"

        deleted = external_boards_service.delete_external_board(canva_board.id)
        assert deleted is True
        assert external_boards_service.get_external_boards_for_project(project_id) == []
        print(f"  ✓ Unified items and mocked Canva board flow passed for items={item_ids}")

    finally:
        db.query(VideoProject).filter(VideoProject.id == project_id).delete()
        db.commit()
        db.close()

    print("✓ test_items_script_excerpt_and_mocked_canva_external_board passed")


def test_note_create_touches_project_updated_at():
    print("\nRunning test_note_create_touches_project_updated_at...")
    db = SessionLocal()
    service = VideoWorkshopService(db)

    project = service.create_video_project(
        VideoProjectCreate(title="Timestamp Touch Test", status="idea", priority=0)
    )
    project_id = project.id
    original_updated_at = project.updated_at

    try:
        time.sleep(0.1)
        service.create_note_for_project(
            project_id,
            VideoProjectNoteCreate(body="Nota de teste para updated_at", note_type="idea"),
        )

        db.expire_all()
        refreshed = db.query(VideoProject).filter(VideoProject.id == project_id).first()
        assert refreshed.updated_at > original_updated_at, (
            f"Expected updated_at to have advanced after note creation. "
            f"original={original_updated_at}, current={refreshed.updated_at}"
        )
        print(f"  ✓ updated_at advanced: {original_updated_at} -> {refreshed.updated_at}")

    finally:
        db.query(VideoProject).filter(VideoProject.id == project_id).delete()
        db.commit()
        db.close()

    print("✓ test_note_create_touches_project_updated_at passed")


def test_canva_oauth_generate_pkce_pair():
    print("\nRunning test_canva_oauth_generate_pkce_pair...")
    db = SessionLocal()
    service = CanvaOAuthService(db)

    verifier, challenge = service.generate_pkce_pair()
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")

    assert 43 <= len(verifier) <= 128, f"Invalid verifier length: {len(verifier)}"
    assert challenge == expected, "PKCE challenge does not match SHA256 verifier digest"
    assert "=" not in challenge, "Challenge should not contain padding"
    db.close()
    print("✓ test_canva_oauth_generate_pkce_pair passed")


def test_canva_oauth_start_authorization_and_callback_and_refresh():
    print("\nRunning test_canva_oauth_start_authorization_and_callback_and_refresh...")
    db = SessionLocal()
    service = CanvaOAuthService(db)
    reset_canva_oauth_tables(db)

    with patch.dict(
        os.environ,
        {
            "CANVA_CLIENT_ID": "client-123",
            "CANVA_CLIENT_SECRET": "secret-xyz",
            "CANVA_REDIRECT_URI": "http://127.0.0.1:8000/canva/oauth/callback",
            "CANVA_SCOPES": "design:content:write design:meta:read",
        },
        clear=False,
    ):
        authorization_url = service.start_authorization(redirect_after="/scripts/12")
        parsed = urlparse(authorization_url)
        params = parse_qs(parsed.query)

        assert params["client_id"] == ["client-123"]
        assert params["response_type"] == ["code"]
        assert params["redirect_uri"] == ["http://127.0.0.1:8000/canva/oauth/callback"]
        assert params["scope"] == ["design:content:write design:meta:read"]
        assert params["code_challenge_method"] == ["S256"]
        assert "state" in params and params["state"][0]
        assert "code_challenge" in params and params["code_challenge"][0]

        saved_state = db.query(CanvaOAuthState).filter(CanvaOAuthState.state == params["state"][0]).first()
        assert saved_state is not None, "OAuth state was not persisted"
        assert saved_state.redirect_after == "/scripts/12"

        issued_refresh_token = "refresh-token-1"

        def mock_post(url, auth=None, data=None, headers=None, timeout=None):
            assert url.endswith("/oauth/token")
            assert data["grant_type"] == "authorization_code"
            assert data["code_verifier"] == saved_state.code_verifier
            return MockHTTPResponse(
                {
                    "access_token": "access-token-1",
                    "refresh_token": issued_refresh_token,
                    "token_type": "Bearer",
                    "scope": "design:content:write design:meta:read",
                    "expires_in": 3600,
                }
            )

        with patch("src.services.canva_oauth_service.requests.post", side_effect=mock_post):
            token = service.handle_callback(code="auth-code-1", state=saved_state.state)

        assert token.access_token == "access-token-1"
        assert token.refresh_token == "refresh-token-1"
        db.refresh(saved_state)
        assert saved_state.used_at is not None, "OAuth state should be marked as used"

        def mock_refresh_post(url, auth=None, data=None, headers=None, timeout=None):
            assert data["grant_type"] == "refresh_token"
            assert data["refresh_token"] == "refresh-token-1"
            return MockHTTPResponse(
                {
                    "access_token": "access-token-2",
                    "refresh_token": "refresh-token-2",
                    "token_type": "Bearer",
                    "scope": "design:content:write design:meta:read",
                    "expires_in": 7200,
                }
            )

        with patch("src.services.canva_oauth_service.requests.post", side_effect=mock_refresh_post):
            refreshed = service.refresh_access_token()

        assert refreshed.access_token == "access-token-2"
        assert refreshed.refresh_token == "refresh-token-2", "Refresh token should rotate when provider returns a new one"

    reset_canva_oauth_tables(db)
    db.close()
    print("✓ test_canva_oauth_start_authorization_and_callback_and_refresh passed")


def test_canva_oauth_valid_access_token_fallback_and_auto_refresh():
    print("\nRunning test_canva_oauth_valid_access_token_fallback_and_auto_refresh...")
    db = SessionLocal()
    service = CanvaOAuthService(db)
    reset_canva_oauth_tables(db)

    with patch.dict(os.environ, {"CANVA_ACCESS_TOKEN": "dev-fallback-token"}, clear=False):
        assert service.get_valid_access_token() == "dev-fallback-token"

    token = CanvaOAuthToken(
        provider="canva",
        access_token="old-access-token",
        refresh_token="old-refresh-token",
        token_type="Bearer",
        scopes="design:content:write design:meta:read",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db.add(token)
    db.commit()

    with patch.dict(
        os.environ,
        {
            "CANVA_CLIENT_ID": "client-123",
            "CANVA_CLIENT_SECRET": "secret-xyz",
            "CANVA_REDIRECT_URI": "http://127.0.0.1:8000/canva/oauth/callback",
        },
        clear=False,
    ):
        def mock_refresh_post(url, auth=None, data=None, headers=None, timeout=None):
            return MockHTTPResponse(
                {
                    "access_token": "fresh-access-token",
                    "refresh_token": "fresh-refresh-token",
                    "token_type": "Bearer",
                    "scope": "design:content:write design:meta:read",
                    "expires_in": 3600,
                }
            )

        with patch("src.services.canva_oauth_service.requests.post", side_effect=mock_refresh_post):
            resolved = service.get_valid_access_token()

        assert resolved == "fresh-access-token"
        stored = db.query(CanvaOAuthToken).filter(CanvaOAuthToken.provider == "canva").first()
        assert stored.refresh_token == "fresh-refresh-token"

    reset_canva_oauth_tables(db)
    db.close()
    print("✓ test_canva_oauth_valid_access_token_fallback_and_auto_refresh passed")


def test_canva_oauth_status_route_and_external_board_token_usage():
    print("\nRunning test_canva_oauth_status_route_and_external_board_token_usage...")
    db = SessionLocal()
    reset_canva_oauth_tables(db)

    token = CanvaOAuthToken(
        provider="canva",
        access_token="opaque-access-token",
        refresh_token="opaque-refresh-token",
        token_type="Bearer",
        scopes="design:content:write design:meta:read",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(token)
    db.commit()
    db.close()

    client = TestClient(app)
    response = client.get("/canva/oauth/status")
    assert response.status_code == 200, response.text
    payload = response.json()
    parsed = CanvaOAuthStatusRead(**payload)
    assert parsed.connected is True
    assert "access_token" not in payload and "refresh_token" not in payload

    db = SessionLocal()
    project = VideoWorkshopService(db).create_video_project(
        VideoProjectCreate(title="OAuth External Board", status="idea", priority=0)
    )
    external_service = ExternalBoardsService(db)

    def mock_request(method, url, headers=None, json=None, timeout=None):
        assert headers["Authorization"] == "Bearer service-token"
        assert method == "POST"
        assert url.endswith("/designs")
        return MockHTTPResponse(
            {
                "design": {
                    "id": "design-from-oauth",
                    "title": "OAuth Board",
                    "urls": {
                        "edit_url": "https://www.canva.com/design/oauth/edit",
                        "view_url": "https://www.canva.com/design/oauth/view",
                    },
                }
            }
        )

    with patch("src.services.external_boards_service.CanvaOAuthService.get_valid_access_token", return_value="service-token"):
        with patch("src.services.external_boards_service.requests.request", side_effect=mock_request):
            board = external_service.create_canva_board_for_project(project.id)

    assert board.external_id == "design-from-oauth"
    assert board.provider == "canva"

    db.query(VideoProject).filter(VideoProject.id == project.id).delete()
    reset_canva_oauth_tables(db)
    db.commit()
    db.close()
    print("✓ test_canva_oauth_status_route_and_external_board_token_usage passed")


def test_open_canva_route_redirects_without_exposing_board_url_in_ui_flow():
    print("\nRunning test_open_canva_route_redirects_without_exposing_board_url_in_ui_flow...")
    db = SessionLocal()
    reset_canva_oauth_tables(db)
    external_id = f"redirect-{int(time.time() * 1000)}"
    project = VideoWorkshopService(db).create_video_project(
        VideoProjectCreate(title="Open Canva Redirect", status="idea", priority=0)
    )
    board = create_mock_canva_board(ExternalBoardsService(db), project.id, external_id=external_id)
    board_id = board.id
    db.close()

    client = TestClient(app)

    with patch(
        "src.api.routes.external_boards.ExternalBoardsService.get_canva_open_url",
        return_value=f"https://www.canva.com/design/{external_id}/edit?token=fresh",
    ):
        response = client.get(f"/external-boards/{board_id}/open-canva", follow_redirects=False)

    assert response.status_code == 307, response.text
    assert response.headers["location"].startswith(f"https://www.canva.com/design/{external_id}/edit")

    cleanup_db = SessionLocal()
    cleanup_db.query(VideoProject).filter(VideoProject.id == project.id).delete()
    cleanup_db.commit()
    cleanup_db.close()
    print("✓ test_open_canva_route_redirects_without_exposing_board_url_in_ui_flow passed")


if __name__ == "__main__":
    try:
        test_tiptap_word_count()
        test_video_projects_crud_and_cascade()
        test_items_script_excerpt_and_mocked_canva_external_board()
        test_note_create_touches_project_updated_at()
        test_canva_oauth_generate_pkce_pair()
        test_canva_oauth_start_authorization_and_callback_and_refresh()
        test_canva_oauth_valid_access_token_fallback_and_auto_refresh()
        test_canva_oauth_status_route_and_external_board_token_usage()
        test_open_canva_route_redirects_without_exposing_board_url_in_ui_flow()
        print("\nAll video workshop tests passed successfully!")
    except AssertionError as e:
        print(f"\nAssertion error: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
