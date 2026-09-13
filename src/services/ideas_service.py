from typing import Optional, Tuple, List

from sqlalchemy.orm import Session

from src.models.video_workshop import VideoProject
from src.repositories.video_workshop_repository import VideoWorkshopRepository
from src.schemas.ideas import IdeaCreate, IdeaUpdate
from src.schemas.video_workshop import VideoProjectCreate, VideoProjectUpdate


class IdeasService:
    def __init__(self, db: Session):
        self.repo = VideoWorkshopRepository(db)

    def create(self, payload: IdeaCreate) -> VideoProject:
        return self.repo.create_video_project(
            VideoProjectCreate(
                title=payload.title,
                description=payload.description,
                niche=payload.niche,
                status=payload.status,
                priority=payload.priority,
            )
        )

    def get(self, idea_id: int) -> Optional[VideoProject]:
        return self.repo.get_video_project_by_id(idea_id)

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        status: Optional[str] = None,
        niche: Optional[str] = None,
    ) -> Tuple[List[VideoProject], int]:
        return self.repo.list_video_projects(
            limit=limit,
            offset=offset,
            search=search,
            status=status,
            niche=niche,
            video_format=None,
        )

    def update(self, idea_id: int, payload: IdeaUpdate) -> Optional[VideoProject]:
        update = VideoProjectUpdate(**payload.model_dump(exclude_unset=True))
        return self.repo.update_video_project(idea_id, update)

    def archive(self, idea_id: int) -> Optional[VideoProject]:
        return self.repo.update_video_project(
            idea_id,
            VideoProjectUpdate(status="archived"),
        )

    def delete(self, idea_id: int) -> bool:
        return self.repo.delete_video_project(idea_id)
