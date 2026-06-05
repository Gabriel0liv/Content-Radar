from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from src.db.session import get_db
from src.services.search_service import SearchService
from src.schemas.search import (
    SearchConfigCreate,
    SearchConfigUpdate,
    SearchConfigRead,
    SearchConfigListResponse,
    SearchRunRead,
    SearchRunCompletePayload,
    SearchRunFailPayload
)

configs_router = APIRouter()
runs_router = APIRouter()

# ----------------- SEARCH CONFIGS ENDPOINTS -----------------

@configs_router.get("", response_model=SearchConfigListResponse)
def list_configs(db: Session = Depends(get_db)):
    """
    Lists all non-archived search configurations.
    """
    service = SearchService(db)
    configs = service.list_configs(include_archived=False)
    return {"configs": configs, "total": len(configs)}

@configs_router.post("", response_model=SearchConfigRead)
def create_config(payload: SearchConfigCreate, db: Session = Depends(get_db)):
    """
    Creates a new search configuration.
    """
    service = SearchService(db)
    return service.create_config(payload)

@configs_router.get("/{id}", response_model=SearchConfigRead)
def get_config(id: int, db: Session = Depends(get_db)):
    """
    Gets a search configuration by ID.
    """
    service = SearchService(db)
    config = service.get_config(id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuração de pesquisa não encontrada")
    return config

@configs_router.patch("/{id}", response_model=SearchConfigRead)
def update_config(id: int, payload: SearchConfigUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing search configuration.
    """
    service = SearchService(db)
    config = service.update_config(id, payload)
    if not config:
        raise HTTPException(status_code=404, detail="Configuração de pesquisa não encontrada")
    return config

@configs_router.post("/{id}/run", response_model=SearchRunRead)
def trigger_run(id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Triggers a manual search execution, queuing a new search run and triggering n8n webhook asynchronously if configured.
    """
    service = SearchService(db)
    try:
        run = service.trigger_search_run(id, background_tasks)
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Internal server / webhook scheduling error
        raise HTTPException(status_code=502, detail=str(e))

@configs_router.get("/{id}/runs", response_model=List[SearchRunRead])
def list_runs(id: int, db: Session = Depends(get_db)):
    """
    Lists recent runs for a given configuration.
    """
    service = SearchService(db)
    return service.list_runs_for_config(id)


# ----------------- SEARCH RUNS ENDPOINTS -----------------

@runs_router.post("/{id}/start", response_model=SearchRunRead)
def start_run(id: int, db: Session = Depends(get_db)):
    """
    Mark a search run as running (called by external agent/n8n).
    """
    service = SearchService(db)
    run = service.start_run(id)
    if not run:
        raise HTTPException(status_code=404, detail="Execução de pesquisa não encontrada")
    return run

@runs_router.post("/{id}/complete", response_model=SearchRunRead)
def complete_run(id: int, payload: SearchRunCompletePayload, db: Session = Depends(get_db)):
    """
    Mark a search run as completed with metrics (called by external agent/n8n).
    """
    service = SearchService(db)
    run = service.complete_run(id, payload)
    if not run:
        raise HTTPException(status_code=404, detail="Execução de pesquisa não encontrada")
    return run

@runs_router.post("/{id}/fail", response_model=SearchRunRead)
def fail_run(id: int, payload: SearchRunFailPayload, db: Session = Depends(get_db)):
    """
    Mark a search run as failed with error details (called by external agent/n8n).
    """
    service = SearchService(db)
    run = service.fail_run(id, payload)
    if not run:
        raise HTTPException(status_code=404, detail="Execução de pesquisa não encontrada")
    return run
