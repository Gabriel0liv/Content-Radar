# Import all models so Base has them registered before env.py imports Base
from src.db.session import Base
from src.models.content_item import ContentItem, ContentItemEvent  # noqa
from src.models.search import SearchConfig, SearchRun  # noqa
from src.models.reference import ReferenceSource, ReferenceImportJob, Transcript, TranscriptSegment  # noqa
from src.models.video_workshop import (
    VideoProject,
    VideoProjectNote,
    VideoProjectReference,
    VideoProjectAudioIdea,
    VideoProjectItem,
    VideoProjectBoardNode,
    VideoProjectBoardEdge,
    VideoProjectExternalBoard,
)  # noqa
