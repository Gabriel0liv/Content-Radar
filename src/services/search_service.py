import os
import requests
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import BackgroundTasks
from src.repositories.search_repository import SearchRepository
from src.schemas.search import (
    SearchConfigCreate,
    SearchConfigUpdate,
    SearchRunCompletePayload,
    SearchRunFailPayload,
)
from src.models.search import SearchConfig, SearchRun


def content_matches_structured_search(item, topic_rows, config) -> bool:
    minimum_topic_confidence = getattr(config, "minimum_topic_confidence", None)
    if minimum_topic_confidence is None:
        minimum_topic_confidence = 0.0

    qualified_topic_ids = {
        int(row.topic_id)
        for row in topic_rows
        if float(getattr(row, "confidence", 0.0) or 0.0) >= float(minimum_topic_confidence)
    }
    included = {int(value) for value in (getattr(config, "included_topic_ids", None) or [])}
    excluded = {int(value) for value in (getattr(config, "excluded_topic_ids", None) or [])}

    if excluded & qualified_topic_ids:
        return False
    if included and not (included & qualified_topic_ids):
        return False

    minimum_ratio = getattr(config, "minimum_performance_ratio", None)
    if minimum_ratio is not None:
        ratio = getattr(item, "performance_ratio", None)
        if ratio is None or float(ratio) < float(minimum_ratio):
            return False
    return True


class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SearchRepository(db)

    def list_configs(self, include_archived: bool = False) -> List[SearchConfig]:
        return self.repo.list_configs(include_archived)

    def get_config(self, config_id: int) -> Optional[SearchConfig]:
        return self.repo.get_config_by_id(config_id)

    def create_config(self, config_in: SearchConfigCreate) -> SearchConfig:
        return self.repo.create_config(config_in)

    def update_config(self, config_id: int, config_in: SearchConfigUpdate) -> Optional[SearchConfig]:
        return self.repo.update_config(config_id, config_in)

    def list_runs_for_config(self, config_id: int, limit: int = 50) -> List[SearchRun]:
        return self.repo.list_runs_by_config_id(config_id, limit)

    def trigger_search_run(self, config_id: int, background_tasks: BackgroundTasks) -> SearchRun:
        config = self.repo.get_config_by_id(config_id)
        if not config:
            raise ValueError(f"Configuração com ID {config_id} não existe.")
        if config.status != "active":
            raise ValueError("Apenas configurações com status 'active' podem ser executadas.")

        run = self.repo.create_run(config_id, trigger_source="manual")
        webhook_url = os.getenv("N8N_SEARCH_WEBHOOK_URL")
        if webhook_url:
            background_tasks.add_task(self.send_webhook_background, run.id, config_id, webhook_url)
        return run

    def send_webhook_background(self, run_id: int, config_id: int, webhook_url: str):
        from src.db.session import SessionLocal
        db = SessionLocal()
        try:
            repo = SearchRepository(db)
            run = repo.get_run_by_id(run_id)
            if not run:
                return
            payload = {"search_config_id": config_id, "search_run_id": run_id}
            try:
                response = requests.post(webhook_url, json=payload, timeout=5)
                if not response.ok:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                run.error_message = f"Falha ao chamar o webhook do n8n: {str(e)}"
                repo.save_run(run)
        finally:
            db.close()

    def start_run(self, run_id: int) -> Optional[SearchRun]:
        run = self.repo.get_run_by_id(run_id)
        if not run:
            return None
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        return self.repo.save_run(run)

    def complete_run(self, run_id: int, payload: SearchRunCompletePayload) -> Optional[SearchRun]:
        run = self.repo.get_run_by_id(run_id)
        if not run:
            return None
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        run.items_found = payload.items_found
        run.items_inserted = payload.items_inserted
        run.items_updated = payload.items_updated
        if payload.raw_summary_json:
            run.raw_summary_json = payload.raw_summary_json
        return self.repo.save_run(run)

    def fail_run(self, run_id: int, payload: SearchRunFailPayload) -> Optional[SearchRun]:
        run = self.repo.get_run_by_id(run_id)
        if not run:
            return None
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = payload.error_message
        if payload.raw_summary_json:
            run.raw_summary_json = payload.raw_summary_json
        return self.repo.save_run(run)
