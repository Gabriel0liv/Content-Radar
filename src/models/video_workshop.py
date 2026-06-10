from sqlalchemy import Column, BigInteger, Text, Integer, Float, DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.session import Base

class VideoProject(Base):
    __tablename__ = "video_projects"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    working_title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    niche = Column(Text, nullable=True)
    target_platform = Column(Text, nullable=True)
    video_format = Column(Text, nullable=True)
    target_duration_seconds = Column(Integer, nullable=True)
    status = Column(Text, nullable=False, server_default="idea")
    priority = Column(Integer, nullable=False, server_default="0")
    thumbnail_url = Column(Text, nullable=True)
    script_text = Column(Text, nullable=False, server_default="")
    script_content_json = Column(JSONB, nullable=True)
    word_count = Column(Integer, nullable=False, server_default="0")
    estimated_duration_seconds = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    project_notes = relationship("VideoProjectNote", back_populates="video_project", cascade="all, delete-orphan")
    references = relationship("VideoProjectReference", back_populates="video_project", cascade="all, delete-orphan")
    audio_ideas = relationship("VideoProjectAudioIdea", back_populates="video_project", cascade="all, delete-orphan")
    board_nodes = relationship("VideoProjectBoardNode", back_populates="video_project", cascade="all, delete-orphan")
    board_edges = relationship("VideoProjectBoardEdge", back_populates="video_project", cascade="all, delete-orphan")
    items = relationship("VideoProjectItem", back_populates="video_project", cascade="all, delete-orphan")
    external_boards = relationship("VideoProjectExternalBoard", back_populates="video_project", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('idea', 'researching', 'scripting', 'reviewing', 'ready', 'produced', 'archived')",
            name="check_video_projects_status"
        ),
        Index("idx_video_projects_status", status),
        Index("idx_video_projects_niche", niche),
        Index("idx_video_projects_created_at_desc", created_at.desc()),
        Index("idx_video_projects_updated_at_desc", updated_at.desc()),
    )


class VideoProjectNote(Base):
    __tablename__ = "video_project_notes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_project_id = Column(BigInteger, ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False)
    note_type = Column(Text, nullable=False, server_default="idea")
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="open")
    pinned = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    video_project = relationship("VideoProject", back_populates="project_notes")

    __table_args__ = (
        CheckConstraint(
            "note_type IN ('idea', 'research', 'script_note', 'production_note', 'music_idea', 'thumbnail_idea', 'editing_note', 'todo', 'other')",
            name="check_video_project_notes_note_type"
        ),
        CheckConstraint(
            "status IN ('open', 'done', 'archived')",
            name="check_video_project_notes_status"
        ),
        Index("idx_video_project_notes_project_id", video_project_id),
        Index("idx_video_project_notes_note_type", note_type),
        Index("idx_video_project_notes_status", status),
        Index("idx_video_project_notes_pinned", pinned),
        Index("idx_video_project_notes_created_at_desc", created_at.desc()),
    )


class VideoProjectReference(Base):
    __tablename__ = "video_project_references"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_project_id = Column(BigInteger, ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False)
    content_item_id = Column(BigInteger, ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True)
    reference_source_id = Column(BigInteger, ForeignKey("reference_sources.id", ondelete="SET NULL"), nullable=True)
    transcript_id = Column(BigInteger, ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True)
    external_url = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    video_project = relationship("VideoProject", back_populates="references")
    content_item = relationship("ContentItem")
    reference_source = relationship("ReferenceSource")
    transcript = relationship("Transcript")

    __table_args__ = (
        Index("idx_video_project_references_project_id", video_project_id),
        Index("idx_video_project_references_content_item_id", content_item_id),
        Index("idx_video_project_references_reference_source_id", reference_source_id),
        Index("idx_video_project_references_transcript_id", transcript_id),
    )


class VideoProjectAudioIdea(Base):
    __tablename__ = "video_project_audio_ideas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_project_id = Column(BigInteger, ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False)
    audio_title = Column(Text, nullable=True)
    audio_url = Column(Text, nullable=True)
    audio_type = Column(Text, nullable=True)
    mood = Column(Text, nullable=True)
    source_platform = Column(Text, nullable=True)
    license_notes = Column(Text, nullable=True)
    usage_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    video_project = relationship("VideoProject", back_populates="audio_ideas")

    __table_args__ = (
        Index("idx_video_project_audio_ideas_project_id", video_project_id),
        Index("idx_video_project_audio_ideas_audio_type", audio_type),
        Index("idx_video_project_audio_ideas_mood", mood),
    )


class VideoProjectItem(Base):
    """Unified workshop element — replaces separate notes/refs/audio in new UI."""
    __tablename__ = "video_project_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_project_id = Column(BigInteger, ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(Text, nullable=False, server_default="note")
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    source_kind = Column(Text, nullable=True, server_default="manual")
    source_id = Column(BigInteger, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    status = Column(Text, nullable=False, server_default="open")
    pinned = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    video_project = relationship("VideoProject", back_populates="items")
    board_nodes = relationship("VideoProjectBoardNode", back_populates="item")

    __table_args__ = (
        Index("idx_vpi_project_id2", video_project_id),
        Index("idx_vpi_item_type2", item_type),
        Index("idx_vpi_status2", status),
        Index("idx_vpi_pinned2", pinned),
    )


class VideoProjectBoardNode(Base):
    __tablename__ = "video_project_board_nodes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_project_id = Column(BigInteger, ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(BigInteger, ForeignKey("video_project_items.id", ondelete="SET NULL"), nullable=True)
    node_key = Column(Text, nullable=False)
    node_type = Column(Text, nullable=False, server_default="note")
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    x = Column(Float, nullable=False, server_default="0")
    y = Column(Float, nullable=False, server_default="0")
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    color = Column(Text, nullable=True)
    data_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    video_project = relationship("VideoProject", back_populates="board_nodes")
    item = relationship("VideoProjectItem", back_populates="board_nodes")

    __table_args__ = (
        UniqueConstraint("video_project_id", "node_key", name="unique_video_project_board_nodes_project_id_node_key"),
        Index("idx_video_project_board_nodes_project_id", video_project_id),
        Index("idx_video_project_board_nodes_node_type", node_type),
    )


class VideoProjectBoardEdge(Base):
    __tablename__ = "video_project_board_edges"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_project_id = Column(BigInteger, ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False)
    edge_key = Column(Text, nullable=False)
    source_node_key = Column(Text, nullable=False)
    target_node_key = Column(Text, nullable=False)
    label = Column(Text, nullable=True)
    data_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    video_project = relationship("VideoProject", back_populates="board_edges")

    __table_args__ = (
        UniqueConstraint("video_project_id", "edge_key", name="unique_video_project_board_edges_project_id_edge_key"),
        Index("idx_video_project_board_edges_project_id", video_project_id),
        Index("idx_video_project_board_edges_source", source_node_key),
        Index("idx_video_project_board_edges_target", target_node_key),
    )


class VideoProjectExternalBoard(Base):
    __tablename__ = "video_project_external_boards"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_project_id = Column(BigInteger, ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False)
    provider = Column(Text, nullable=False)
    external_id = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    view_url = Column(Text, nullable=True)
    edit_url = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    video_project = relationship("VideoProject", back_populates="external_boards")

    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_video_project_external_boards_provider_external_id"),
        CheckConstraint("provider IN ('miro', 'canva')", name="check_video_project_external_boards_provider"),
        Index("idx_video_project_external_boards_project_id", video_project_id),
        Index("idx_video_project_external_boards_provider", provider),
    )
