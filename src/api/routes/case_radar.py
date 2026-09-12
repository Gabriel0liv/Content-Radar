from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.case_radar import (
    CaseResearchCreate,
    CaseResearchQueryRead,
    CaseResearchRunListResponse,
    CaseResearchRunRead,
    ResearchCasePatch,
    ResearchCaseRead,
    ResearchSourceRead,
)
from src.services.case_radar_service import CaseRadarService


router = APIRouter()


def get_case_radar_service(db: Session = Depends(get_db)) -> CaseRadarService:
    return CaseRadarService(db)


@router.post("/runs", response_model=CaseResearchRunRead, status_code=status.HTTP_201_CREATED)
def create_run(
    request: CaseResearchCreate,
    service: CaseRadarService = Depends(get_case_radar_service),
):
    return service.create_run(request)


@router.get("/runs", response_model=CaseResearchRunListResponse)
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: CaseRadarService = Depends(get_case_radar_service),
):
    items, total = service.list_runs(limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/runs/{run_id}", response_model=CaseResearchRunRead)
def get_run(run_id: int, service: CaseRadarService = Depends(get_case_radar_service)):
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Pesquisa do Case Radar não encontrada")
    return run


@router.post("/runs/{run_id}/cancel", response_model=CaseResearchRunRead)
def cancel_run(run_id: int, service: CaseRadarService = Depends(get_case_radar_service)):
    run = service.cancel_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Pesquisa do Case Radar não encontrada")
    return run


@router.get("/runs/{run_id}/queries", response_model=list[CaseResearchQueryRead])
def list_queries(run_id: int, service: CaseRadarService = Depends(get_case_radar_service)):
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Pesquisa do Case Radar não encontrada")
    return service.list_queries(run_id)


@router.get("/runs/{run_id}/sources", response_model=list[ResearchSourceRead])
def list_sources(run_id: int, service: CaseRadarService = Depends(get_case_radar_service)):
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Pesquisa do Case Radar não encontrada")
    return service.list_sources(run_id)


@router.get("/runs/{run_id}/cases", response_model=list[ResearchCaseRead])
def list_cases(run_id: int, service: CaseRadarService = Depends(get_case_radar_service)):
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Pesquisa do Case Radar não encontrada")
    return service.list_cases(run_id)


@router.get("/cases/{case_id}", response_model=ResearchCaseRead)
def get_case(case_id: int, service: CaseRadarService = Depends(get_case_radar_service)):
    case = service.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Caso não encontrado")
    return case


@router.patch("/cases/{case_id}", response_model=ResearchCaseRead)
def update_case(
    case_id: int,
    patch: ResearchCasePatch,
    service: CaseRadarService = Depends(get_case_radar_service),
):
    try:
        case = service.update_case(case_id, patch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if case is None:
        raise HTTPException(status_code=404, detail="Caso não encontrado")
    return case
