from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone

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
    VideoProjectBoardEdgeCreate
)

class VideoWorkshopRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Video Projects CRUD ---
    def create_video_project(self, project_in: VideoProjectCreate) -> VideoProject:
        project_data = project_in.model_dump()
        db_project = VideoProject(**project_data)
        self.db.add(db_project)
        self.db.commit()
        self.db.refresh(db_project)
        return db_project

    def update_video_project(
        self,
        project_id: int,
        project_in: VideoProjectUpdate,
        word_count: Optional[int] = None,
        estimated_duration_seconds: Optional[int] = None
    ) -> Optional[VideoProject]:
        db_project = self.get_video_project_by_id(project_id)
        if not db_project:
            return None

        update_data = project_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_project, key, value)

        if word_count is not None:
            db_project.word_count = word_count
        if estimated_duration_seconds is not None:
            db_project.estimated_duration_seconds = estimated_duration_seconds

        db_project.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(db_project)
        return db_project

    def get_video_project_by_id(self, project_id: int) -> Optional[VideoProject]:
        return self.db.query(VideoProject).filter(VideoProject.id == project_id).first()

    def list_video_projects(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        status: Optional[str] = None,
        niche: Optional[str] = None,
        video_format: Optional[str] = None
    ) -> Tuple[List[VideoProject], int]:
        query = self.db.query(VideoProject)

        if status and status != "Todos":
            query = query.filter(VideoProject.status == status)
        if niche and niche != "Todos":
            query = query.filter(VideoProject.niche.ilike(f"%{niche}%"))
        if video_format and video_format != "Todos":
            query = query.filter(VideoProject.video_format == video_format)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (VideoProject.title.ilike(search_pattern)) |
                (func.coalesce(VideoProject.working_title, '').ilike(search_pattern)) |
                (func.coalesce(VideoProject.description, '').ilike(search_pattern))
            )

        total = query.count()
        items = query.order_by(VideoProject.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    def delete_video_project(self, project_id: int) -> bool:
        db_project = self.get_video_project_by_id(project_id)
        if not db_project:
            return False
        self.db.delete(db_project)
        self.db.commit()
        return True


    # --- Notes CRUD ---
    def get_note_by_id(self, note_id: int) -> Optional[VideoProjectNote]:
        return self.db.query(VideoProjectNote).filter(VideoProjectNote.id == note_id).first()

    def list_notes_by_project(self, project_id: int) -> List[VideoProjectNote]:
        return self.db.query(VideoProjectNote).filter(
            VideoProjectNote.video_project_id == project_id
        ).order_by(VideoProjectNote.pinned.desc(), VideoProjectNote.created_at.desc()).all()

    def create_note(self, project_id: int, note_in: VideoProjectNoteCreate) -> VideoProjectNote:
        note_data = note_in.model_dump()
        note_data["video_project_id"] = project_id
        db_note = VideoProjectNote(**note_data)
        self.db.add(db_note)
        self.db.commit()
        self.db.refresh(db_note)
        return db_note

    def update_note(self, note_id: int, note_in: VideoProjectNoteUpdate) -> Optional[VideoProjectNote]:
        db_note = self.get_note_by_id(note_id)
        if not db_note:
            return None

        update_data = note_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_note, key, value)

        db_note.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(db_note)
        return db_note

    def delete_note(self, note_id: int) -> bool:
        db_note = self.get_note_by_id(note_id)
        if not db_note:
            return False
        self.db.delete(db_note)
        self.db.commit()
        return True


    # --- References CRUD ---
    def get_reference_by_id(self, reference_id: int) -> Optional[VideoProjectReference]:
        return self.db.query(VideoProjectReference).filter(VideoProjectReference.id == reference_id).first()

    def list_references_by_project(self, project_id: int) -> List[VideoProjectReference]:
        return self.db.query(VideoProjectReference).filter(
            VideoProjectReference.video_project_id == project_id
        ).order_by(VideoProjectReference.created_at.desc()).all()

    def create_reference(self, project_id: int, ref_in: VideoProjectReferenceCreate) -> VideoProjectReference:
        ref_data = ref_in.model_dump()
        ref_data["video_project_id"] = project_id
        db_ref = VideoProjectReference(**ref_data)
        self.db.add(db_ref)
        self.db.commit()
        self.db.refresh(db_ref)
        return db_ref

    def delete_reference(self, reference_id: int) -> bool:
        db_ref = self.get_reference_by_id(reference_id)
        if not db_ref:
            return False
        self.db.delete(db_ref)
        self.db.commit()
        return True


    # --- Audio Ideas CRUD ---
    def get_audio_idea_by_id(self, audio_id: int) -> Optional[VideoProjectAudioIdea]:
        return self.db.query(VideoProjectAudioIdea).filter(VideoProjectAudioIdea.id == audio_id).first()

    def list_audio_ideas_by_project(self, project_id: int) -> List[VideoProjectAudioIdea]:
        return self.db.query(VideoProjectAudioIdea).filter(
            VideoProjectAudioIdea.video_project_id == project_id
        ).order_by(VideoProjectAudioIdea.created_at.desc()).all()

    def create_audio_idea(self, project_id: int, audio_in: VideoProjectAudioIdeaCreate) -> VideoProjectAudioIdea:
        audio_data = audio_in.model_dump()
        audio_data["video_project_id"] = project_id
        db_audio = VideoProjectAudioIdea(**audio_data)
        self.db.add(db_audio)
        self.db.commit()
        self.db.refresh(db_audio)
        return db_audio

    def delete_audio_idea(self, audio_id: int) -> bool:
        db_audio = self.get_audio_idea_by_id(audio_id)
        if not db_audio:
            return False
        self.db.delete(db_audio)
        self.db.commit()
        return True


    # --- Board Nodes CRUD ---
    def get_board_node_by_id(self, node_id: int) -> Optional[VideoProjectBoardNode]:
        return self.db.query(VideoProjectBoardNode).filter(VideoProjectBoardNode.id == node_id).first()

    def list_board_nodes_by_project(self, project_id: int) -> List[VideoProjectBoardNode]:
        return self.db.query(VideoProjectBoardNode).filter(
            VideoProjectBoardNode.video_project_id == project_id
        ).all()

    def create_board_node(self, project_id: int, node_in: VideoProjectBoardNodeCreate) -> VideoProjectBoardNode:
        node_data = node_in.model_dump()
        node_data["video_project_id"] = project_id
        db_node = VideoProjectBoardNode(**node_data)
        self.db.add(db_node)
        self.db.commit()
        self.db.refresh(db_node)
        return db_node

    def update_board_node(self, node_id: int, node_in: VideoProjectBoardNodeUpdate) -> Optional[VideoProjectBoardNode]:
        db_node = self.get_board_node_by_id(node_id)
        if not db_node:
            return None

        update_data = node_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_node, key, value)

        db_node.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(db_node)
        return db_node

    def delete_board_node(self, node_id: int) -> bool:
        db_node = self.get_board_node_by_id(node_id)
        if not db_node:
            return False
        self.db.delete(db_node)
        self.db.commit()
        return True


    # --- Board Edges CRUD ---
    def get_board_edge_by_id(self, edge_id: int) -> Optional[VideoProjectBoardEdge]:
        return self.db.query(VideoProjectBoardEdge).filter(VideoProjectBoardEdge.id == edge_id).first()

    def list_board_edges_by_project(self, project_id: int) -> List[VideoProjectBoardEdge]:
        return self.db.query(VideoProjectBoardEdge).filter(
            VideoProjectBoardEdge.video_project_id == project_id
        ).all()

    def create_board_edge(self, project_id: int, edge_in: VideoProjectBoardEdgeCreate) -> VideoProjectBoardEdge:
        edge_data = edge_in.model_dump()
        edge_data["video_project_id"] = project_id
        db_edge = VideoProjectBoardEdge(**edge_data)
        self.db.add(db_edge)
        self.db.commit()
        self.db.refresh(db_edge)
        return db_edge

    def delete_board_edge(self, edge_id: int) -> bool:
        db_edge = self.get_board_edge_by_id(edge_id)
        if not db_edge:
            return False
        self.db.delete(db_edge)
        self.db.commit()
        return True


    # --- Full Board State Sync ---
    def sync_board_state(
        self,
        project_id: int,
        nodes_in: List[VideoProjectBoardNodeCreate],
        edges_in: List[VideoProjectBoardEdgeCreate]
    ) -> Tuple[List[VideoProjectBoardNode], List[VideoProjectBoardEdge]]:
        # Delete existing
        self.db.query(VideoProjectBoardEdge).filter(VideoProjectBoardEdge.video_project_id == project_id).delete()
        self.db.query(VideoProjectBoardNode).filter(VideoProjectBoardNode.video_project_id == project_id).delete()

        # Insert new nodes
        nodes = []
        for n_in in nodes_in:
            n_data = n_in.model_dump()
            n_data["video_project_id"] = project_id
            db_n = VideoProjectBoardNode(**n_data)
            self.db.add(db_n)
            nodes.append(db_n)

        # Insert new edges
        edges = []
        for e_in in edges_in:
            e_data = e_in.model_dump()
            e_data["video_project_id"] = project_id
            db_e = VideoProjectBoardEdge(**e_data)
            self.db.add(db_e)
            edges.append(db_e)

        self.db.commit()

        # Refresh
        for n in nodes:
            self.db.refresh(n)
        for e in edges:
            self.db.refresh(e)

        return nodes, edges
