import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.models.video_workshop import VideoProject, VideoProjectExternalBoard


class ExternalBoardsService:
    def __init__(self, db: Session):
        self.db = db

    def _touch_project(self, project: VideoProject) -> None:
        project.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(project)

    def _get_project(self, project_id: int) -> Optional[VideoProject]:
        return self.db.query(VideoProject).filter(VideoProject.id == project_id).first()

    def _get_external_board(self, board_id: int) -> Optional[VideoProjectExternalBoard]:
        return self.db.query(VideoProjectExternalBoard).filter(VideoProjectExternalBoard.id == board_id).first()

    def _get_canva_token(self) -> str:
        token = (os.getenv("CANVA_ACCESS_TOKEN", "") or "").strip()
        if not token:
            raise RuntimeError("Canva não configurado: CANVA_ACCESS_TOKEN ausente")
        return token

    def _get_canva_base_url(self) -> str:
        base_url = (os.getenv("CANVA_BASE_URL", "") or "").strip().rstrip("/")
        if not base_url:
            raise RuntimeError("Canva não configurado: CANVA_BASE_URL ausente")
        return base_url

    def _extract_design_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        design = payload.get("design")
        if isinstance(design, dict):
            return design
        return payload

    def _extract_board_links(self, payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
        design_payload = self._extract_design_payload(payload)
        links = design_payload.get("links") if isinstance(design_payload.get("links"), dict) else {}
        urls = design_payload.get("urls") if isinstance(design_payload.get("urls"), dict) else {}
        self_link = links.get("self") or urls.get("self")
        self_href = self_link.get("href") if isinstance(self_link, dict) else self_link
        edit_link = links.get("edit") or urls.get("edit")
        view_link = links.get("view") or urls.get("view")
        edit_href = edit_link.get("href") if isinstance(edit_link, dict) else edit_link
        view_href = view_link.get("href") if isinstance(view_link, dict) else view_link
        return {
            "view_url": (
                design_payload.get("viewLink")
                or design_payload.get("view_url")
                or design_payload.get("viewUrl")
                or urls.get("view_url")
                or view_href
                or self_href
            ),
            "edit_url": (
                design_payload.get("editLink")
                or design_payload.get("edit_url")
                or design_payload.get("editUrl")
                or design_payload.get("url")
                or urls.get("edit_url")
                or edit_href
                or self_href
            ),
        }

    def _extract_external_id(self, payload: Dict[str, Any]) -> Optional[str]:
        design_payload = self._extract_design_payload(payload)
        direct_candidates = [
            design_payload.get("id"),
            design_payload.get("design_id"),
            design_payload.get("designId"),
            design_payload.get("external_id"),
            design_payload.get("externalId"),
        ]
        for candidate in direct_candidates:
            if candidate:
                return str(candidate)
        return None

    def _canva_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_canva_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _canva_request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = requests.request(
            method=method,
            url=f"{self._get_canva_base_url()}{path}",
            headers=self._canva_headers(),
            json=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            try:
                error_payload = response.json()
                message = error_payload.get("message") or error_payload.get("type") or response.text
            except ValueError:
                message = response.text
            raise RuntimeError(f"Erro ao chamar Canva: {message}")
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}

    def _upsert_external_board(
        self,
        project: VideoProject,
        provider: str,
        external_id: str,
        title: Optional[str],
        view_url: Optional[str],
        edit_url: Optional[str],
        metadata_json: Optional[Dict[str, Any]],
    ) -> VideoProjectExternalBoard:
        existing = (
            self.db.query(VideoProjectExternalBoard)
            .filter(
                VideoProjectExternalBoard.provider == provider,
                VideoProjectExternalBoard.external_id == external_id,
            )
            .first()
        )
        if existing:
            existing.video_project_id = project.id
            existing.title = title or existing.title
            existing.view_url = view_url or existing.view_url
            existing.edit_url = edit_url or existing.edit_url
            existing.metadata_json = metadata_json or existing.metadata_json
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            self._touch_project(project)
            return existing

        external_board = VideoProjectExternalBoard(
            video_project_id=project.id,
            provider=provider,
            external_id=external_id,
            title=title,
            view_url=view_url,
            edit_url=edit_url,
            metadata_json=metadata_json,
        )
        self.db.add(external_board)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise RuntimeError("Conflito ao salvar o board externo no banco")
        self.db.refresh(external_board)
        self._touch_project(project)
        return external_board

    def get_external_boards_for_project(self, project_id: int) -> List[VideoProjectExternalBoard]:
        project = self._get_project(project_id)
        if not project:
            raise ValueError("Projeto de vídeo não encontrado")
        return (
            self.db.query(VideoProjectExternalBoard)
            .filter(VideoProjectExternalBoard.video_project_id == project_id)
            .order_by(VideoProjectExternalBoard.created_at.desc())
            .all()
        )

    def create_canva_board_for_project(self, project_id: int) -> VideoProjectExternalBoard:
        project = self._get_project(project_id)
        if not project:
            raise ValueError("Projeto de vídeo não encontrado")

        payload = {
            "type": "type_and_asset",
            "design_type": {
                "type": "preset",
                "name": "whiteboard",
            },
            "title": project.title or "Untitled",
        }
        board_response = self._canva_request("POST", "/designs", payload)
        external_id = self._extract_external_id(board_response)
        if not external_id:
            raise RuntimeError("Resposta do Canva sem identificador do design")
        links = self._extract_board_links(board_response)
        design_payload = self._extract_design_payload(board_response)
        return self._upsert_external_board(
            project=project,
            provider="canva",
            external_id=external_id,
            title=design_payload.get("title") or project.title,
            view_url=links["view_url"],
            edit_url=links["edit_url"],
            metadata_json=design_payload,
        )

    def refresh_canva_design_urls(self, external_board_id: int) -> VideoProjectExternalBoard:
        external_board = self._get_external_board(external_board_id)
        if not external_board:
            raise ValueError("Board externo não encontrado")
        if external_board.provider != "canva":
            raise ValueError("Refresh de URL suportado apenas para boards Canva")

        project = external_board.video_project
        response = self._canva_request("GET", f"/designs/{external_board.external_id}")
        links = self._extract_board_links(response)
        design_payload = self._extract_design_payload(response)

        external_board.title = design_payload.get("title") or external_board.title
        external_board.view_url = links["view_url"] or external_board.view_url
        external_board.edit_url = links["edit_url"] or external_board.edit_url
        external_board.metadata_json = {
            **(external_board.metadata_json or {}),
            **design_payload,
            "canva_last_url_refresh_at": datetime.now(timezone.utc).isoformat(),
        }
        external_board.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(external_board)
        if project:
            self._touch_project(project)
        return external_board

    def delete_external_board(self, external_board_id: int) -> bool:
        external_board = self._get_external_board(external_board_id)
        if not external_board:
            return False
        project = external_board.video_project
        self.db.delete(external_board)
        self.db.commit()
        if project:
            self._touch_project(project)
        return True
