from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, Index, Integer, Text, UniqueConstraint
from sqlalchemy.sql import func

from src.db.session import Base


class DiscoveryTerm(Base):
    __tablename__ = "discovery_terms"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    normalized_term = Column(Text, nullable=False)
    display_name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    entity_id = Column(BigInteger, nullable=True)
    usage_count = Column(Integer, nullable=False, server_default="0")
    video_count = Column(Integer, nullable=False, server_default="0")
    channel_count = Column(Integer, nullable=False, server_default="0")
    relevance_score = Column(Float, nullable=False, server_default="0")
    suppressed = Column(Boolean, nullable=False, server_default="false")
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("normalized_term", "type", "entity_id", name="uq_discovery_terms_identity"),
        Index("idx_discovery_terms_normalized_term", normalized_term),
        Index("idx_discovery_terms_type", type),
        Index("idx_discovery_terms_relevance_desc", relevance_score.desc()),
    )
