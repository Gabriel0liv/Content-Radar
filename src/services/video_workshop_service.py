from sqlalchemy.orm import Session
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone

from src.repositories.video_workshop_repository import VideoWorkshopRepository
from src.models.video_workshop import (
    VideoProject,
    VideoProjectNote,
    VideoProjectReference,
    VideoProjectAudioIdea,
    VideoProjectBoardNode,
    VideoProjectBoardEdge
)
from src.schemas.video_workshop import (
    VideoProjectCreate,
    VideoProjectUpdate,
    VideoProjectNoteCreate,
    VideoProjectNoteUpdate,
    VideoProjectReferenceCreate,
    VideoProjectAudioIdeaCreate,
    VideoProjectBoardNodeCreate,
    VideoProjectBoardNodeUpdate,
    VideoProjectBoardEdgeCreate,
    VideoProjectBoardStateRead
)

def extract_text_from_tiptap_json(node: Any) -> str:
    """
    Recursively extracts plain text from a Tiptap JSON node structure.
    """
    if not node:
        return ""
    if isinstance(node, dict):
        if node.get("type") == "text" and "text" in node:
            return node["text"]
        content = node.get("content", [])
        if isinstance(content, list):
            return " ".join(filter(None, [extract_text_from_tiptap_json(c) for c in content]))
    elif isinstance(node, list):
        return " ".join(filter(None, [extract_text_from_tiptap_json(c) for c in node]))
    return ""

def calculate_word_and_duration(text: str) -> Tuple[int, int]:
    """
    Returns (word_count, estimated_duration_seconds) based on 150 words per minute reading speed.
    """
    if not text or not text.strip():
        return 0, 0
    words = text.split()
    word_count = len(words)
    # 150 words per minute -> 150 words / 60 seconds -> 2.5 words per second
    # duration = word_count / 2.5
    duration_seconds = int(round((word_count / 150.0) * 60.0))
    return word_count, duration_seconds


class VideoWorkshopService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = VideoWorkshopRepository(db)

    # --- Video Projects ---
    def create_video_project(self, project_in: VideoProjectCreate) -> VideoProject:
        return self.repo.create_video_project(project_in)

    def update_video_project(self, project_id: int, project_in: VideoProjectUpdate) -> Optional[VideoProject]:
        db_project = self.repo.get_video_project_by_id(project_id)
        if not db_project:
            return None

        # Determine if script text or JSON changed to recompute duration/word count
        word_count = None
        estimated_duration_seconds = None

        script_text = project_in.script_text
        script_json = project_in.script_content_json

        # If plain text is explicitly passed
        if script_text is not None:
            word_count, estimated_duration_seconds = calculate_word_and_duration(script_text)
        # Else if only rich JSON content is updated, extract text to compute
        elif script_json is not None:
            plain_text = extract_text_from_tiptap_json(script_json)
            word_count, estimated_duration_seconds = calculate_word_and_duration(plain_text)

        return self.repo.update_video_project(
            project_id=project_id,
            project_in=project_in,
            word_count=word_count,
            estimated_duration_seconds=estimated_duration_seconds
        )

    def get_video_project(self, project_id: int) -> Optional[VideoProject]:
        return self.repo.get_video_project_by_id(project_id)

    def list_video_projects(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        status: Optional[str] = None,
        niche: Optional[str] = None,
        video_format: Optional[str] = None
    ) -> Tuple[List[VideoProject], int]:
        return self.repo.list_video_projects(
            limit=limit,
            offset=offset,
            search=search,
            status=status,
            niche=niche,
            video_format=video_format
        )

    def archive_video_project(self, project_id: int) -> Optional[VideoProject]:
        update_payload = VideoProjectUpdate(status="archived")
        return self.repo.update_video_project(project_id, update_payload)

    def delete_video_project(self, project_id: int) -> bool:
        return self.repo.delete_video_project(project_id)


    # --- Notes ---
    def get_note(self, note_id: int) -> Optional[VideoProjectNote]:
        return self.repo.get_note_by_id(note_id)

    def list_notes_for_project(self, project_id: int) -> List[VideoProjectNote]:
        return self.repo.list_notes_by_project(project_id)

    def create_note_for_project(self, project_id: int, note_in: VideoProjectNoteCreate) -> VideoProjectNote:
        return self.repo.create_note(project_id, note_in)

    def update_note(self, note_id: int, note_in: VideoProjectNoteUpdate) -> Optional[VideoProjectNote]:
        return self.repo.update_note(note_id, note_in)

    def delete_note(self, note_id: int) -> bool:
        return self.repo.delete_note(note_id)


    # --- References ---
    def list_references_for_project(self, project_id: int) -> List[VideoProjectReference]:
        return self.repo.list_references_by_project(project_id)

    def create_reference_for_project(self, project_id: int, ref_in: VideoProjectReferenceCreate) -> VideoProjectReference:
        return self.repo.create_reference(project_id, ref_in)

    def delete_reference(self, reference_id: int) -> bool:
        return self.repo.delete_reference(reference_id)


    # --- Audio Ideas ---
    def list_audio_ideas_for_project(self, project_id: int) -> List[VideoProjectAudioIdea]:
        return self.repo.list_audio_ideas_by_project(project_id)

    def create_audio_idea_for_project(self, project_id: int, audio_in: VideoProjectAudioIdeaCreate) -> VideoProjectAudioIdea:
        return self.repo.create_audio_idea(project_id, audio_in)

    def delete_audio_idea(self, audio_id: int) -> bool:
        return self.repo.delete_audio_idea(audio_id)


    # --- BoardState ---
    def get_board_state_for_project(self, project_id: int) -> Dict[str, Any]:
        nodes = self.repo.list_board_nodes_by_project(project_id)
        edges = self.repo.list_board_edges_by_project(project_id)
        return {
            "nodes": nodes,
            "edges": edges
        }

    def save_board_state_for_project(
        self,
        project_id: int,
        nodes_in: List[VideoProjectBoardNodeCreate],
        edges_in: List[VideoProjectBoardEdgeCreate]
    ) -> Dict[str, Any]:
        nodes, edges = self.repo.sync_board_state(project_id, nodes_in, edges_in)
        return {
            "nodes": nodes,
            "edges": edges
        }

    def create_board_node_for_project(self, project_id: int, node_in: VideoProjectBoardNodeCreate) -> VideoProjectBoardNode:
        return self.repo.create_board_node(project_id, node_in)

    def update_board_node(self, node_id: int, node_in: VideoProjectBoardNodeUpdate) -> Optional[VideoProjectBoardNode]:
        return self.repo.update_board_node(node_id, node_in)

    def delete_board_node(self, node_id: int) -> bool:
        return self.repo.delete_board_node(node_id)

    def create_board_edge_for_project(self, project_id: int, edge_in: VideoProjectBoardEdgeCreate) -> VideoProjectBoardEdge:
        return self.repo.create_board_edge(project_id, edge_in)

    def delete_board_edge(self, edge_id: int) -> bool:
        return self.repo.delete_board_edge(edge_id)
