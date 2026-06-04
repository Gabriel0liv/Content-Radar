from sqlalchemy import Column, BigInteger, Text, Float, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.session import Base

class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(BigInteger, primary_key=True)
    source = Column(Text, nullable=False)
    external_id = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False, server_default="video")
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=False)
    channel_title = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    views = Column(BigInteger, server_default="0")
    likes = Column(BigInteger, server_default="0")
    comments = Column(BigInteger, server_default="0")
    views_per_day = Column(Float, server_default="0.0")
    score = Column(Float, server_default="0.0")
    topic_seed = Column(Text, nullable=True)
    discovery_query = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    country_code = Column(Text, nullable=True)
    status = Column(Text, server_default="new")
    notes = Column(Text, nullable=True)
    raw_json = Column(JSONB, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    selected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)
    production_notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="unique_source_external_id"),
        CheckConstraint(
            "status IN ('new', 'reviewed', 'selected', 'rejected', 'produced', 'archived')",
            name="check_content_items_status"
        ),
        Index("idx_content_items_score_desc", score.desc()),
        Index("idx_content_items_published_at_desc", published_at.desc()),
        Index("idx_content_items_status", status),
        Index("idx_content_items_source_external_id", source, external_id),
        Index("idx_content_items_content_type", content_type),
        Index("idx_content_items_topic_seed", topic_seed),
    )

    events = relationship("ContentItemEvent", back_populates="content_item", cascade="all, delete-orphan")


class ContentItemEvent(Base):
    __tablename__ = "content_item_events"

    id = Column(BigInteger, primary_key=True)
    content_item_id = Column(BigInteger, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    data = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_content_item_events_content_item_id", content_item_id),
    )

    content_item = relationship("ContentItem", back_populates="events")
