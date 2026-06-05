from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from src.models.search import SearchConfig, SearchRun
from src.schemas.search import SearchConfigCreate, SearchConfigUpdate

class SearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_config_by_id(self, config_id: int) -> Optional[SearchConfig]:
        return self.db.query(SearchConfig).filter(SearchConfig.id == config_id).first()

    def list_configs(self, include_archived: bool = False) -> List[SearchConfig]:
        query = self.db.query(SearchConfig)
        if not include_archived:
            query = query.filter(SearchConfig.status != "archived")
        return query.order_by(SearchConfig.created_at.desc()).all()

    def create_config(self, config_in: SearchConfigCreate) -> SearchConfig:
        config_data = config_in.model_dump()
        db_config = SearchConfig(**config_data)
        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)
        return db_config

    def update_config(self, config_id: int, config_in: SearchConfigUpdate) -> Optional[SearchConfig]:
        db_config = self.get_config_by_id(config_id)
        if not db_config:
            return None
        
        update_data = config_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_config, key, value)
            
        db_config.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(db_config)
        return db_config

    def get_run_by_id(self, run_id: int) -> Optional[SearchRun]:
        return self.db.query(SearchRun).filter(SearchRun.id == run_id).first()

    def create_run(self, config_id: int, trigger_source: str = "manual") -> SearchRun:
        db_run = SearchRun(
            search_config_id=config_id,
            status="queued",
            trigger_source=trigger_source,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(db_run)
        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def list_runs_by_config_id(self, config_id: int, limit: int = 50) -> List[SearchRun]:
        return self.db.query(SearchRun)\
            .filter(SearchRun.search_config_id == config_id)\
            .order_by(SearchRun.created_at.desc())\
            .limit(limit)\
            .all()

    def save_run(self, run: SearchRun) -> SearchRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
