from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple
from datetime import datetime, timezone

from src.models.video_workshop import (
    VideoProject,
    VideoProjectNote,
    VideoProjectReference,
    VideoProjectAudioIdea,
    VideoProjectItem,
)
from src.schemas.video_workshop import (
    VideoProjectCreate,
    VideoProjectUpdate,
    VideoProjectNoteCreate,
    VideoProjectNoteUpdate,
    VideoProjectReferenceCreate,
    VideoProjectAudioIdeaCreate,
    VideoProjectItemCreate,
    VideoProjectItemUpdate,
)

class VideoWorkshopRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Video Projects CRUD ──────────────────────────────────────────────────

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
        items = query.order_by(VideoProject.updated_at.desc()).offset(offset).limit(limit).all()
        return items, total

    def delete_video_project(self, project_id: int) -> bool:
        db_project = self.get_video_project_by_id(project_id)
        if not db_project:
            return False
        self.db.delete(db_project)
        self.db.commit()
        return True

    def touch_video_project(self, project_id: int) -> None:
        """Update updated_at on video_projects whenever a sub-resource changes."""
        db_project = self.get_video_project_by_id(project_id)
        if db_project:
            db_project.updated_at = datetime.now(timezone.utc)
            self.db.commit()

    # ── Notes CRUD (legacy) ──────────────────────────────────────────────────

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
        self.touch_video_project(project_id)
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
        self.touch_video_project(db_note.video_project_id)
        return db_note

    def delete_note(self, note_id: int) -> bool:
        db_note = self.get_note_by_id(note_id)
        if not db_note:
            return False
        project_id = db_note.video_project_id
        self.db.delete(db_note)
        self.db.commit()
        self.touch_video_project(project_id)
        return True

    # ── References CRUD (legacy) ─────────────────────────────────────────────

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
        self.touch_video_project(project_id)
        return db_ref

    def delete_reference(self, reference_id: int) -> bool:
        db_ref = self.get_reference_by_id(reference_id)
        if not db_ref:
            return False
        project_id = db_ref.video_project_id
        self.db.delete(db_ref)
        self.db.commit()
        self.touch_video_project(project_id)
        return True

    # ── Audio Ideas CRUD (legacy) ────────────────────────────────────────────

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
        self.touch_video_project(project_id)
        return db_audio

    def delete_audio_idea(self, audio_id: int) -> bool:
        db_audio = self.get_audio_idea_by_id(audio_id)
        if not db_audio:
            return False
        project_id = db_audio.video_project_id
        self.db.delete(db_audio)
        self.db.commit()
        self.touch_video_project(project_id)
        return True

    # ── VideoProjectItem CRUD ────────────────────────────────────────────────

    def get_item_by_id(self, item_id: int) -> Optional[VideoProjectItem]:
        return self.db.query(VideoProjectItem).filter(VideoProjectItem.id == item_id).first()

    def list_items_by_project(
        self,
        project_id: int,
        item_type: Optional[str] = None,
        status: Optional[str] = None,
        pinned: Optional[bool] = None
    ) -> List[VideoProjectItem]:
        query = self.db.query(VideoProjectItem).filter(VideoProjectItem.video_project_id == project_id)
        if item_type:
            query = query.filter(VideoProjectItem.item_type == item_type)
        if status:
            query = query.filter(VideoProjectItem.status == status)
        if pinned is not None:
            query = query.filter(VideoProjectItem.pinned == pinned)
        return query.order_by(VideoProjectItem.pinned.desc(), VideoProjectItem.updated_at.desc()).all()

    def create_item(self, project_id: int, item_in: VideoProjectItemCreate) -> VideoProjectItem:
        item_data = item_in.model_dump()
        item_data["video_project_id"] = project_id
        db_item = VideoProjectItem(**item_data)
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        self.touch_video_project(project_id)
        return db_item

    def update_item(self, item_id: int, item_in: VideoProjectItemUpdate) -> Optional[VideoProjectItem]:
        db_item = self.get_item_by_id(item_id)
        if not db_item:
            return None
        update_data = item_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)
        db_item.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(db_item)
        self.touch_video_project(db_item.video_project_id)
        return db_item

    def delete_item(self, item_id: int) -> bool:
        db_item = self.get_item_by_id(item_id)
        if not db_item:
            return False
        project_id = db_item.video_project_id
        self.db.delete(db_item)
        self.db.commit()
        self.touch_video_project(project_id)
        return True

    def create_item_from_script_excerpt(
        self, project_id: int, text: str, title: Optional[str] = None
    ) -> VideoProjectItem:
        item_in = VideoProjectItemCreate(
            item_type="script_excerpt",
            title=title or "Trecho do Roteiro",
            body=text,
            source_kind="script",
            status="open",
            pinned=False
        )
        return self.create_item(project_id, item_in)
