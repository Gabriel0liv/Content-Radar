from sqlalchemy import BigInteger, Column, DateTime, Float, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from src.db.session import Base


class ChannelProfile(Base):
    __tablename__ = "channel_profiles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    channel_id = Column(Text, nullable=False, unique=True)
    channel_title = Column(Text, nullable=True)
    sample_count = Column(Integer, nullable=False, server_default="0")
    dominant_topics_json = Column(JSONB, nullable=True, server_default='[]')
    recent_views_median = Column(Float, nullable=True)
    recent_views_per_day_median = Column(Float, nullable=True)
    recent_age_adjusted_samples = Column(Integer, nullable=False, server_default="0")
    last_profiled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_channel_profiles_channel_id", channel_id),
        Index("idx_channel_profiles_last_profiled_at", last_profiled_at),
    )
