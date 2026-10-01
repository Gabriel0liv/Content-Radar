from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.speech import SpeechSpeakerProfile


_RAW_SPEAKER_RE = re.compile(r"^SPEAKER_[A-Za-z0-9_-]+$")


class SpeechSpeakerProfilesService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _clean_mapping(mapping: dict[str, str]) -> dict[str, str]:
        if not isinstance(mapping, dict) or not mapping:
            raise ValueError("O perfil precisa de pelo menos um mapeamento de speaker")
        clean: dict[str, str] = {}
        for raw, display in mapping.items():
            raw_name = str(raw).strip()
            display_name = str(display).strip()
            if not _RAW_SPEAKER_RE.fullmatch(raw_name):
                raise ValueError("Labels crus devem usar o formato SPEAKER_XX")
            if not display_name:
                raise ValueError("Nome de exibição do speaker não pode ser vazio")
            clean[raw_name] = display_name
        return clean

    def _all(self) -> list[SpeechSpeakerProfile]:
        rows = list(self.db.execute(select(SpeechSpeakerProfile).order_by(SpeechSpeakerProfile.name, SpeechSpeakerProfile.id)).scalars())
        return sorted(rows, key=lambda item: (item.name.casefold(), item.id or 0))

    def _ensure_unique(self, name: str, *, excluding_id: int | None = None) -> None:
        normalized = name.casefold()
        for profile in self._all():
            if excluding_id is not None and profile.id == excluding_id:
                continue
            if profile.name.strip().casefold() == normalized:
                raise ValueError("Já existe um perfil de speakers com este nome")

    @staticmethod
    def serialize(profile: SpeechSpeakerProfile) -> dict[str, Any]:
        return {
            "id": profile.id,
            "name": profile.name,
            "mapping": deepcopy(profile.mapping_json or {}),
            "notes": profile.notes,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }

    def list_profiles(self) -> list[dict[str, Any]]:
        return [self.serialize(profile) for profile in self._all()]

    def get_profile(self, profile_id_or_name: int | str) -> SpeechSpeakerProfile | None:
        if isinstance(profile_id_or_name, int) or str(profile_id_or_name).isdigit():
            return self.db.get(SpeechSpeakerProfile, int(profile_id_or_name))
        normalized = str(profile_id_or_name).strip().casefold()
        return next((profile for profile in self._all() if profile.name.strip().casefold() == normalized), None)

    def create_profile(self, name: str, mapping: dict[str, str], notes: str | None = None) -> SpeechSpeakerProfile:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Nome do perfil é obrigatório")
        self._ensure_unique(clean_name)
        profile = SpeechSpeakerProfile(name=clean_name, mapping_json=self._clean_mapping(mapping), notes=notes)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_profile(
        self,
        profile_id: int,
        *,
        name: str | None = None,
        mapping: dict[str, str] | None = None,
        notes: str | None = None,
    ) -> SpeechSpeakerProfile:
        profile = self.db.get(SpeechSpeakerProfile, profile_id)
        if profile is None:
            raise FileNotFoundError("Perfil de speakers não encontrado")
        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise ValueError("Nome do perfil é obrigatório")
            self._ensure_unique(clean_name, excluding_id=profile.id)
            profile.name = clean_name
        if mapping is not None:
            profile.mapping_json = self._clean_mapping(mapping)
        if notes is not None:
            profile.notes = notes
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete_profile(self, profile_id: int) -> bool:
        profile = self.db.get(SpeechSpeakerProfile, profile_id)
        if profile is None:
            return False
        self.db.delete(profile)
        self.db.commit()
        return True
