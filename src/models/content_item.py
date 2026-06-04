from sqlalchemy import Column, BigInteger, String, Float, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.session import Base

class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(BigInteger, primary_key=True, index=True)
    source = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    content_type = Column(String, nullable=False, server_default="video")
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    url = Column(String, nullable=False)
    channel_title = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    views = Column(BigInteger, server_default="0")
    likes = Column(BigInteger, server_default="0")
    comments = Column(BigInteger, server_default="0")
    views_per_day = Column(Float, server_default="0.0")
    score = Column(Float, server_default="0.0")
    topic_seed = Column(String, nullable=True)
    discovery_query = Column(String, nullable=True)
    language = Column(String, nullable=True)
    country_code = Column(String, nullable=True)
    status = Column(String, server_default="new")
    notes = Column(String, nullable=True)
    raw_json = Column(JSONB, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    selected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(String, nullable=True)
    production_notes = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="unique_source_external_id"),
        CheckConstraint(
            "status IN ('new', 'reviewed', 'selected', 'rejected', 'produced', 'archived')",
            name="check_content_items_status"
        )
    )

    events = relationship("ContentItemEvent", back_populates="content_item", cascade="all, delete-orphan")


class ContentItemEvent(Base):
    __tablename__ = "content_item_events"

    id = Column(BigInteger, primary_key=True, index=True)
    content_item_id = Column(BigInteger, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    data = Column(JSONB, nullable=True)

    content_item = relationship("ContentItem", back_populates="events")
