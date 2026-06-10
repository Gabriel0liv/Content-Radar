import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import requests
from requests.auth import HTTPBasicAuth
from sqlalchemy.orm import Session

from src.models.canva_oauth import CanvaOAuthState, CanvaOAuthToken


@dataclass
class CanvaOAuthConfig:
    client_id: Optional[str]
    client_secret: Optional[str]
    redirect_uri: Optional[str]
    base_url: str
    authorize_url: str
    scopes: str
    dev_access_token: Optional[str]


class CanvaOAuthService:
    OAUTH_STATE_TTL_MINUTES = 10
    TOKEN_EXPIRY_SAFETY_SECONDS = 120

    def __init__(self, db: Session):
        self.db = db

    def get_config(self) -> CanvaOAuthConfig:
        return CanvaOAuthConfig(
            client_id=(os.getenv("CANVA_CLIENT_ID") or "").strip() or None,
            client_secret=(os.getenv("CANVA_CLIENT_SECRET") or "").strip() or None,
            redirect_uri=(os.getenv("CANVA_REDIRECT_URI") or "").strip() or None,
            base_url=(os.getenv("CANVA_BASE_URL") or "https://api.canva.com/rest/v1").strip().rstrip("/"),
            authorize_url=(os.getenv("CANVA_OAUTH_AUTHORIZE_URL") or "https://www.canva.com/api/oauth/authorize").strip().rstrip("/"),
            scopes=(os.getenv("CANVA_SCOPES") or "design:content:write design:meta:read").strip(),
            dev_access_token=(os.getenv("CANVA_ACCESS_TOKEN") or "").strip() or None,
        )

    def _require_oauth_config(self) -> CanvaOAuthConfig:
        config = self.get_config()
        missing = [
            name
            for name, value in (
                ("CANVA_CLIENT_ID", config.client_id),
                ("CANVA_CLIENT_SECRET", config.client_secret),
                ("CANVA_REDIRECT_URI", config.redirect_uri),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"Canva não configurado: {', '.join(missing)} ausente(s)")
        return config

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _is_expiring(self, expires_at: datetime) -> bool:
        return expires_at <= self._now() + timedelta(seconds=self.TOKEN_EXPIRY_SAFETY_SECONDS)

    def _mask_error(self, message: str) -> str:
        if not message:
            return "Erro desconhecido ao comunicar com o Canva"
        return message.replace("\n", " ").strip()

    def _token_endpoint(self, config: CanvaOAuthConfig) -> str:
        return f"{config.base_url}/oauth/token"

    def _extract_error_message(self, response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if isinstance(payload, dict):
            for key in ("message", "error_description", "error", "type"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return self._mask_error(value)
        return self._mask_error(response.text or f"HTTP {response.status_code}")

    def _token_response_to_expiry(self, payload: dict) -> datetime:
        expires_in = payload.get("expires_in")
        try:
            expires_seconds = int(expires_in)
        except (TypeError, ValueError):
            expires_seconds = 3600
        return self._now() + timedelta(seconds=expires_seconds)

    def _get_token_row(self) -> Optional[CanvaOAuthToken]:
        return (
            self.db.query(CanvaOAuthToken)
            .filter(CanvaOAuthToken.provider == "canva")
            .first()
        )

    def _save_token_payload(self, payload: dict) -> CanvaOAuthToken:
        token_row = self._get_token_row()
        if token_row is None:
            token_row = CanvaOAuthToken(provider="canva", access_token="", refresh_token="", expires_at=self._now())
            self.db.add(token_row)

        token_row.access_token = payload["access_token"]
        token_row.refresh_token = payload["refresh_token"]
        token_row.token_type = payload.get("token_type") or "Bearer"
        scopes = payload.get("scope")
        token_row.scopes = " ".join(scopes) if isinstance(scopes, list) else scopes
        token_row.expires_at = self._token_response_to_expiry(payload)
        token_row.updated_at = self._now()
        self.db.commit()
        self.db.refresh(token_row)
        return token_row

    def generate_pkce_pair(self) -> tuple[str, str]:
        verifier = secrets.token_urlsafe(64).rstrip("=")
        verifier = verifier[:128]
        if len(verifier) < 43:
            verifier = (verifier + secrets.token_urlsafe(32)).rstrip("=")
            verifier = verifier[:43]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
        return verifier, challenge

    def start_authorization(self, redirect_after: str | None = None) -> str:
        config = self._require_oauth_config()
        code_verifier, code_challenge = self.generate_pkce_pair()
        state = secrets.token_urlsafe(32)

        auth_state = CanvaOAuthState(
            state=state,
            code_verifier=code_verifier,
            redirect_after=redirect_after,
            scopes=config.scopes,
            expires_at=self._now() + timedelta(minutes=self.OAUTH_STATE_TTL_MINUTES),
        )
        self.db.add(auth_state)
        self.db.commit()

        query = urlencode(
            {
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "response_type": "code",
                "client_id": config.client_id,
                "scope": config.scopes,
                "state": state,
                "redirect_uri": config.redirect_uri,
            }
        )
        return f"{config.authorize_url}?{query}"

    def handle_callback(self, code: str, state: str) -> CanvaOAuthToken:
        config = self._require_oauth_config()
        oauth_state = (
            self.db.query(CanvaOAuthState)
            .filter(CanvaOAuthState.state == state)
            .first()
        )
        if oauth_state is None:
            raise ValueError("State OAuth inválido")
        if oauth_state.used_at is not None:
            raise ValueError("State OAuth já utilizado")
        if oauth_state.expires_at <= self._now():
            raise ValueError("State OAuth expirado")

        response = requests.post(
            self._token_endpoint(config),
            auth=HTTPBasicAuth(config.client_id or "", config.client_secret or ""),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": oauth_state.code_verifier,
                "redirect_uri": config.redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Erro ao conectar com o Canva: {self._extract_error_message(response)}")

        payload = response.json()
        if not payload.get("access_token") or not payload.get("refresh_token"):
            raise RuntimeError("Resposta OAuth do Canva incompleta")

        token_row = self._save_token_payload(payload)
        oauth_state.used_at = self._now()
        self.db.commit()
        return token_row

    def refresh_access_token(self) -> CanvaOAuthToken:
        config = self._require_oauth_config()
        token_row = self._get_token_row()
        if token_row is None:
            raise RuntimeError("Canva não conectado. Acesse /canva/oauth/start para conectar.")

        response = requests.post(
            self._token_endpoint(config),
            auth=HTTPBasicAuth(config.client_id or "", config.client_secret or ""),
            data={
                "grant_type": "refresh_token",
                "refresh_token": token_row.refresh_token,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Erro ao renovar token do Canva: {self._extract_error_message(response)}")

        payload = response.json()
        if not payload.get("access_token") or not payload.get("refresh_token"):
            raise RuntimeError("Resposta de refresh do Canva incompleta")

        return self._save_token_payload(payload)

    def get_valid_access_token(self) -> str:
        token_row = self._get_token_row()
        if token_row is not None:
            if self._is_expiring(token_row.expires_at):
                token_row = self.refresh_access_token()
            return token_row.access_token

        config = self.get_config()
        if config.dev_access_token:
            return config.dev_access_token

        raise RuntimeError("Canva não conectado. Acesse /canva/oauth/start para conectar.")

    def get_status(self):
        config = self.get_config()
        token_row = self._get_token_row()
        using_fallback = token_row is None and bool(config.dev_access_token)
        connected = token_row is not None or using_fallback

        if token_row is not None:
            message = "Canva conectado via OAuth."
        elif using_fallback:
            message = "Usando token de desenvolvimento do .env."
        elif config.client_id and config.client_secret and config.redirect_uri:
            message = "Canva ainda não conectado."
        else:
            message = "Configure CANVA_CLIENT_ID, CANVA_CLIENT_SECRET e CANVA_REDIRECT_URI para usar OAuth."

        return {
            "configured": bool((config.client_id and config.client_secret and config.redirect_uri) or config.dev_access_token),
            "connected": connected,
            "expires_at": token_row.expires_at if token_row is not None else None,
            "scopes": token_row.scopes if token_row is not None else config.scopes,
            "using_dev_token_fallback": using_fallback,
            "message": message,
        }
