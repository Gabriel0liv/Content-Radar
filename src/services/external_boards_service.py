import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.orm import Session

from src.models.video_workshop import VideoProject, VideoProjectExternalBoard, VideoProjectItem


MIRO_BASE_URL = "https://api.miro.com/v2"
SUPPORTED_SYNC_TYPES = [
    "note",
    "reference",
    "script_excerpt",
    "audio",
    "thumbnail",
    "todo",
    "production",
]


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

    def _get_miro_token(self) -> str:
        token = (os.getenv("MIRO_ACCESS_TOKEN", "") or "").strip()
        if not token:
            raise RuntimeError("Miro não configurado")
        return token

    def _extract_board_links(self, payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
        links = payload.get("links") if isinstance(payload.get("links"), dict) else {}
        self_link = links.get("self")
        self_href = self_link.get("href") if isinstance(self_link, dict) else self_link
        return {
            "view_url": payload.get("viewLink") or payload.get("view_url") or self_href,
            "edit_url": payload.get("editLink") or payload.get("edit_url") or self_href,
        }

    def _miro_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_miro_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _miro_post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(
            f"{MIRO_BASE_URL}{path}",
            headers=self._miro_headers(),
            json=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            try:
                error_payload = response.json()
                message = error_payload.get("message") or error_payload.get("type") or response.text
            except ValueError:
                message = response.text
            raise RuntimeError(f"Erro ao chamar Miro: {message}")
        return response.json()

    def get_external_boards_for_project(self, project_id: int) -> List[VideoProjectExternalBoard]:
        return (
            self.db.query(VideoProjectExternalBoard)
            .filter(VideoProjectExternalBoard.video_project_id == project_id)
            .order_by(VideoProjectExternalBoard.created_at.desc())
            .all()
        )

    def create_miro_board_for_project(self, project_id: int) -> VideoProjectExternalBoard:
        project = self._get_project(project_id)
        if not project:
            raise ValueError("Projeto de vídeo não encontrado")

        payload: Dict[str, Any] = {
            "name": project.title[:60] if project.title else "Untitled",
            "description": (project.description or "")[:300],
        }
        team_id = (os.getenv("MIRO_TEAM_ID", "") or "").strip()
        if team_id:
            payload["policy"] = {"teamId": team_id}

        board_response = self._miro_post("/boards", payload)
        links = self._extract_board_links(board_response)

        external_board = VideoProjectExternalBoard(
            video_project_id=project.id,
            provider="miro",
            external_id=str(board_response.get("id")),
            title=board_response.get("name") or project.title,
            view_url=links["view_url"],
            edit_url=links["edit_url"],
            metadata_json=board_response,
        )
        self.db.add(external_board)
        self.db.commit()
        self.db.refresh(external_board)
        self._touch_project(project)
        return external_board

    def create_miro_sticky_note(self, board_id: str, title: Optional[str], body: Optional[str], x: float, y: float) -> Dict[str, Any]:
        content_parts = [part for part in [title, body] if part]
        content = "<br/>".join(content_parts) if content_parts else "Sem conteúdo"
        payload = {
            "data": {"content": content},
            "style": {"fillColor": "light_yellow"},
            "position": {"origin": "center", "x": x, "y": y},
            "geometry": {"width": 220},
        }
        return self._miro_post(f"/boards/{board_id}/sticky_notes", payload)

    def create_miro_shape(self, board_id: str, title: Optional[str], body: Optional[str], x: float, y: float) -> Dict[str, Any]:
        content_parts = [part for part in [title, body] if part]
        content = "<br/>".join(content_parts) if content_parts else "Sem conteúdo"
        payload = {
            "data": {"shape": "round_rectangle", "content": content},
            "style": {"fillColor": "light_blue"},
            "position": {"origin": "center", "x": x, "y": y},
            "geometry": {"width": 280, "height": 120},
        }
        return self._miro_post(f"/boards/{board_id}/shapes", payload)

    def sync_project_items_to_miro(self, project_id: int, board_id: int) -> Dict[str, Any]:
        project = self._get_project(project_id)
        if not project:
            raise ValueError("Projeto de vídeo não encontrado")

        external_board = self._get_external_board(board_id)
        if not external_board or external_board.video_project_id != project_id:
            raise ValueError("Board externo não encontrado para este projeto")
        if external_board.provider != "miro":
            raise ValueError("Sync suportado apenas para boards Miro neste momento")

        pushed_count = 0
        section_count = 0
        x_origin = -1200
        y_origin = -500
        column_gap = 420
        row_gap = 180

        self.create_miro_shape(external_board.external_id, project.title, project.description or "Projeto de vídeo", x_origin, y_origin)
        pushed_count += 1

        if project.script_text and project.script_text.strip():
            excerpt = project.script_text.strip()[:900]
            self.create_miro_sticky_note(external_board.external_id, "Roteiro / Gancho", excerpt, x_origin, y_origin + row_gap)
            pushed_count += 1

        items = (
            self.db.query(VideoProjectItem)
            .filter(
                VideoProjectItem.video_project_id == project_id,
                VideoProjectItem.item_type.in_(SUPPORTED_SYNC_TYPES),
            )
            .order_by(VideoProjectItem.pinned.desc(), VideoProjectItem.updated_at.desc())
            .all()
        )

        grouped_items: Dict[str, List[VideoProjectItem]] = {}
        for item in items:
            grouped_items.setdefault(item.item_type, []).append(item)

        current_x = x_origin + column_gap
        for item_type in SUPPORTED_SYNC_TYPES:
            bucket = grouped_items.get(item_type, [])
            if not bucket:
                continue

            section_count += 1
            self.create_miro_shape(
                external_board.external_id,
                item_type.replace("_", " ").title(),
                f"{len(bucket)} elemento(s)",
                current_x,
                y_origin,
            )
            pushed_count += 1

            current_y = y_origin + row_gap
            for item in bucket:
                sticky_response = self.create_miro_sticky_note(
                    external_board.external_id,
                    item.title or item_type.replace("_", " ").title(),
                    item.body or item.url or "",
                    current_x,
                    current_y,
                )
                current_y += row_gap
                pushed_count += 1

                metadata = dict(item.metadata_json or {})
                miro_items = metadata.get("miro_item_ids")
                if not isinstance(miro_items, list):
                    miro_items = []
                sticky_id = sticky_response.get("id")
                if sticky_id:
                    miro_items.append(str(sticky_id))
                metadata["miro_item_ids"] = miro_items
                metadata["miro_last_board_id"] = external_board.external_id
                metadata["miro_last_pushed_at"] = datetime.now(timezone.utc).isoformat()
                item.metadata_json = metadata

            current_x += column_gap

        board_metadata = dict(external_board.metadata_json or {})
        board_metadata["last_sync_at"] = datetime.now(timezone.utc).isoformat()
        board_metadata["last_sync_summary"] = {
            "pushed_item_count": pushed_count,
            "sections_count": section_count,
            "duplicated_warning": True,
        }
        external_board.metadata_json = board_metadata
        external_board.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(external_board)
        self._touch_project(project)

        return {
            "board": external_board,
            "provider": "miro",
            "pushed_item_count": pushed_count,
            "sections_count": section_count,
            "duplicated_warning": True,
            "synced_at": datetime.now(timezone.utc),
            "message": "Sync manual enviado ao Miro. Esta operação pode duplicar itens se executada novamente.",
        }

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
