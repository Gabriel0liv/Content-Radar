from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.case_radar import CaseSource, ResearchCase, ResearchSource
from src.repositories.case_radar import CaseRadarRepository
from src.schemas.case_radar import CaseResearchCreate, ResearchCasePatch


class CaseRadarService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CaseRadarRepository(db)

    def create_run(self, request: CaseResearchCreate):
        return self.repo.create_run(request.model_dump(mode="json"))

    def list_runs(self, limit: int = 50, offset: int = 0):
        return self.repo.list_runs(limit=limit, offset=offset)

    def get_run(self, run_id: int):
        return self.repo.get_run(run_id)

    def cancel_run(self, run_id: int):
        return self.repo.request_cancel(run_id)

    def list_queries(self, run_id: int):
        return self.repo.list_queries(run_id)

    def list_sources(self, run_id: int):
        return self.repo.list_sources(run_id)

    def list_cases(self, run_id: int):
        return self.repo.list_cases(run_id)

    def get_case(self, case_id: int):
        return self.repo.get_case(case_id)

    def update_case(self, case_id: int, patch: ResearchCasePatch):
        case = self.repo.get_case(case_id)
        if case is None:
            return None

        updates = patch.model_dump(exclude_unset=True)
        selected_source_id = updates.get("selected_primary_source_id")
        if selected_source_id is not None:
            source = self.db.get(ResearchSource, selected_source_id)
            if source is None or source.run_id != case.run_id:
                raise ValueError("Fonte primária selecionada não pertence ao mesmo run")
            linked = self.db.execute(
                select(CaseSource).where(
                    CaseSource.case_id == case_id,
                    CaseSource.source_id == selected_source_id,
                )
            ).scalar_one_or_none()
            if linked is None:
                raise ValueError("Fonte primária precisa estar vinculada ao caso")

        for key, value in updates.items():
            setattr(case, key, value)
        if updates.get("already_used") is True and "status" not in updates:
            case.status = "already_used"

        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case
