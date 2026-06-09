import sys
import src.db.base
from sqlalchemy.exc import IntegrityError
from src.db.session import SessionLocal
from src.models.video_workshop import (
    VideoProject,
    VideoProjectNote,
    VideoProjectReference,
    VideoProjectAudioIdea,
    VideoProjectBoardNode,
    VideoProjectBoardEdge
)
from src.services.video_workshop_service import (
    VideoWorkshopService,
    extract_text_from_tiptap_json,
    calculate_word_and_duration
)
from src.schemas.video_workshop import (
    VideoProjectCreate,
    VideoProjectUpdate,
    VideoProjectNoteCreate,
    VideoProjectNoteUpdate,
    VideoProjectReferenceCreate,
    VideoProjectAudioIdeaCreate,
    VideoProjectBoardNodeCreate,
    VideoProjectBoardEdgeCreate,
    VideoProjectBoardStateRead
)

def test_tiptap_word_count():
    print("Running test_tiptap_word_count...")

    # Case 1: Simple Tiptap JSON node structure
    tiptap_json = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Este é um teste do editor."}
                ]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Outro parágrafo com mais palavras."}
                ]
            }
        ]
    }
    extracted_text = extract_text_from_tiptap_json(tiptap_json)
    assert extracted_text == "Este é um teste do editor. Outro parágrafo com mais palavras.", f"Got '{extracted_text}'"

    word_count, duration = calculate_word_and_duration(extracted_text)
    # 11 words
    assert word_count == 11, f"Expected 11 words, got {word_count}"
    # 11 words at 150 words/min -> (11/150)*60 = 4.4 seconds -> rounds to 4
    assert duration == 4, f"Expected 4 seconds, got {duration}"
    print("✓ Tiptap text parser and word count passed")


def test_video_projects_crud_and_cascade():
    print("\nRunning test_video_projects_crud_and_cascade (DB integration)...")
    db = SessionLocal()
    service = VideoWorkshopService(db)

    # 1. Create a project
    project_payload = VideoProjectCreate(
        title="Novo Vídeo do Canal",
        working_title="Como programar em Python",
        description="Um tutorial prático de Python para iniciantes",
        niche="Tecnologia",
        target_platform="YouTube",
        video_format="Video Normal",
        target_duration_seconds=600,
        status="idea",
        priority=3
    )
    project = service.create_video_project(project_payload)
    project_id = project.id
    print(f"Created video project: ID={project_id}, title='{project.title}'")
    assert project.status == "idea"
    assert project.word_count == 0
    assert project.estimated_duration_seconds is None or project.estimated_duration_seconds == 0

    try:
        # 2. Update script_text and verify calculations
        script_payload = VideoProjectUpdate(
            script_text="Olá pessoal, hoje vamos aprender a programar em Python do zero absoluta. O Python é fantástico."
        )
        updated_project = service.update_video_project(project_id, script_payload)
        # 16 words. (16 / 150) * 60 = 6.4 -> rounds to 6 seconds
        print(f"Updated script: word_count={updated_project.word_count}, estimated_duration={updated_project.estimated_duration_seconds}")
        assert updated_project.word_count == 16
        assert updated_project.estimated_duration_seconds == 6

        # 3. Add a note
        note_payload = VideoProjectNoteCreate(
            note_type="idea",
            title="Gancho inicial",
            body="Começar com uma pergunta instigante sobre o mercado de programação.",
            pinned=True
        )
        note = service.create_note_for_project(project_id, note_payload)
        print(f"Created note: ID={note.id}, type={note.note_type}, pinned={note.pinned}")
        assert note.pinned is True

        # 4. Add a reference
        ref_payload = VideoProjectReferenceCreate(
            external_url="https://docs.python.org",
            title="Documentação Oficial",
            note="Ótimo link para colocar na descrição"
        )
        ref = service.create_reference_for_project(project_id, ref_payload)
        print(f"Created reference: ID={ref.id}, title='{ref.title}'")

        # 5. Add audio idea
        audio_payload = VideoProjectAudioIdeaCreate(
            audio_title="Upbeat Tech Music",
            audio_url="https://example.com/audio.mp3",
            audio_type="background_music",
            mood="energetic"
        )
        audio = service.create_audio_idea_for_project(project_id, audio_payload)
        print(f"Created audio idea: ID={audio.id}, mood='{audio.mood}'")

        # 6. Save visual board state
        board_nodes = [
            VideoProjectBoardNodeCreate(node_key="node1", node_type="note", title="Intro", x=100.0, y=100.0),
            VideoProjectBoardNodeCreate(node_key="node2", node_type="note", title="Body", x=200.0, y=150.0)
        ]
        board_edges = [
            VideoProjectBoardEdgeCreate(edge_key="edge1", source_node_key="node1", target_node_key="node2", label="conecta")
        ]
        board_state = service.save_board_state_for_project(project_id, board_nodes, board_edges)
        print(f"Saved board state: nodes_count={len(board_state['nodes'])}, edges_count={len(board_state['edges'])}")
        assert len(board_state['nodes']) == 2
        assert len(board_state['edges']) == 1

        # Check retrieve
        retrieved_board = service.get_board_state_for_project(project_id)
        assert len(retrieved_board['nodes']) == 2
        assert len(retrieved_board['edges']) == 1

        # 7. Check check constraints on status
        try:
            invalid_status_payload = VideoProjectUpdate(status="invalid_status_value")
            service.update_video_project(project_id, invalid_status_payload)
            assert False, "Expected CheckConstraint error for invalid status"
        except IntegrityError:
            db.rollback()
            print("✓ Check constraint on status rejected invalid value successfully")

        # 8. Check cascade delete
        success = service.delete_video_project(project_id)
        assert success is True
        print(f"Deleted project: ID={project_id}")

        # Assert cascades deleted related entities
        # Check notes
        notes = db.query(VideoProjectNote).filter(VideoProjectNote.video_project_id == project_id).all()
        assert len(notes) == 0, f"Expected notes to be cascading deleted, got {len(notes)}"
        # Check references
        refs = db.query(VideoProjectReference).filter(VideoProjectReference.video_project_id == project_id).all()
        assert len(refs) == 0, f"Expected references to be cascading deleted, got {len(refs)}"
        # Check audio ideas
        audios = db.query(VideoProjectAudioIdea).filter(VideoProjectAudioIdea.video_project_id == project_id).all()
        assert len(audios) == 0, f"Expected audio ideas to be cascading deleted"
        # Check board nodes
        nodes = db.query(VideoProjectBoardNode).filter(VideoProjectBoardNode.video_project_id == project_id).all()
        assert len(nodes) == 0, f"Expected board nodes to be cascading deleted"

        print("✓ Cascade deletes verified successfully")

    finally:
        # Cleanup just in case
        db.query(VideoProject).filter(VideoProject.id == project_id).delete()
        db.commit()
        db.close()

    print("✓ test_video_projects_crud_and_cascade passed")


if __name__ == "__main__":
    try:
        test_tiptap_word_count()
        test_video_projects_crud_and_cascade()
        print("\nAll video workshop tests passed successfully!")
    except AssertionError as e:
        print(f"\nAssertion error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
