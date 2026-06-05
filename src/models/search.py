from sqlalchemy import Column, BigInteger, Text, Integer, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.session import Base

class SearchConfig(Base):
    __tablename__ = "search_configs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Text, nullable=False, server_default="active")
    language = Column(Text, nullable=True, server_default="pt")
    country_code = Column(Text, nullable=True, server_default="BR")
    region_code = Column(Text, nullable=True)
    days_back = Column(Integer, nullable=True, server_default="5")
    min_views = Column(BigInteger, nullable=True, server_default="30000")
    max_results_per_query = Column(Integer, nullable=True, server_default="50")
    sources_json = Column(JSONB, nullable=True, server_default='["youtube", "google_news"]')
    keywords_json = Column(JSONB, nullable=False)
    negative_keywords_json = Column(JSONB, nullable=True, server_default='[]')
    youtube_categories_json = Column(JSONB, nullable=True, server_default='[]')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    runs = relationship("SearchRun", back_populates="search_config", cascade="all, delete-orphan")
    content_items = relationship("ContentItem", back_populates="search_config")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'archived')", name="check_search_configs_status"),
        Index("idx_search_configs_status", status),
        Index("idx_search_configs_name", name),
    )

class SearchRun(Base):
    __tablename__ = "search_runs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    search_config_id = Column(BigInteger, ForeignKey("search_configs.id", ondelete="CASCADE"), nullable=False)
    status = Column(Text, nullable=False, server_default="queued")
    trigger_source = Column(Text, nullable=True, server_default="manual")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    items_found = Column(Integer, server_default="0")
    items_inserted = Column(Integer, server_default="0")
    items_updated = Column(Integer, server_default="0")
    error_message = Column(Text, nullable=True)
    raw_summary_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search_config = relationship("SearchConfig", back_populates="runs")
    content_items = relationship("ContentItem", back_populates="search_run")

    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="check_search_runs_status"),
        Index("idx_search_runs_search_config_id", search_config_id),
        Index("idx_search_runs_status", status),
        Index("idx_search_runs_created_at_desc", created_at.desc()),
    )
