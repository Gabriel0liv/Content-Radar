import sys
import time

import src.db.base
from sqlalchemy.exc import IntegrityError

from src.db.session import SessionLocal
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
from src.services.external_boards_service import ExternalBoardsService
from src.services.video_workshop_service import (
    VideoWorkshopService,
    calculate_word_and_duration,
    extract_text_from_tiptap_json,
)


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


if __name__ == "__main__":
    try:
        test_tiptap_word_count()
        test_video_projects_crud_and_cascade()
        test_items_script_excerpt_and_mocked_canva_external_board()
        test_note_create_touches_project_updated_at()
        print("\nAll video workshop tests passed successfully!")
    except AssertionError as e:
        print(f"\nAssertion error: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
