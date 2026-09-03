from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.session import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    parent_id = Column(BigInteger, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    status = Column(Text, nullable=False, server_default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parent = relationship("Topic", remote_side=[id])
    content_associations = relationship("ContentItemTopic", back_populates="topic", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("type IN ('topic', 'subtopic', 'format', 'series')", name="check_topics_type"),
        CheckConstraint("status IN ('active', 'hidden', 'archived')", name="check_topics_status"),
        UniqueConstraint("normalized_name", "type", "parent_id", name="uq_topics_normalized_type_parent"),
        Index("idx_topics_normalized_name", normalized_name),
        Index("idx_topics_type", type),
    )


class ContentItemTopic(Base):
    __tablename__ = "content_item_topics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    content_item_id = Column(BigInteger, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(BigInteger, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    confidence = Column(Float, nullable=False, server_default="0")
    source = Column(Text, nullable=False)
    signals_json = Column(JSONB, nullable=True, server_default='[]')
    classifier_version = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    topic = relationship("Topic", back_populates="content_associations")

    __table_args__ = (
        UniqueConstraint("content_item_id", "topic_id", name="uq_content_item_topics_item_topic"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="check_content_item_topics_confidence"),
        Index("idx_content_item_topics_content_item_id", content_item_id),
        Index("idx_content_item_topics_topic_id", topic_id),
        Index("idx_content_item_topics_confidence", confidence),
    )
