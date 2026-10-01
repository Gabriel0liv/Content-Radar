from types import SimpleNamespace

import pytest

from src.models.speech import SpeechSpeakerProfile
from src.services.speech_speaker_profiles_service import SpeechSpeakerProfilesService


class ScalarResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def scalars(self):
        return iter(self.rows)


class FakeDb:
    def __init__(self):
        self.rows = []
        self.next_id = 1

    def execute(self, stmt):
        return ScalarResult(self.rows)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self.next_id
            self.next_id += 1
        self.rows.append(obj)

    def get(self, model, key):
        return next((row for row in self.rows if row.id == key), None)

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def delete(self, obj):
        self.rows.remove(obj)


def test_speaker_profile_crud_preserves_raw_to_display_mapping():
    service = SpeechSpeakerProfilesService(FakeDb())
    created = service.create_profile(
        "Entrevista",
        {"SPEAKER_00": "Gabriel", "SPEAKER_01": "Convidado"},
        notes="Perfil recorrente",
    )
    assert created.name == "Entrevista"
    assert created.mapping_json["SPEAKER_00"] == "Gabriel"
    listed = service.list_profiles()
    assert listed[0]["mapping"]["SPEAKER_01"] == "Convidado"

    updated = service.update_profile(created.id, mapping={"SPEAKER_00": "Narrador"})
    assert updated.mapping_json == {"SPEAKER_00": "Narrador"}
    assert service.delete_profile(created.id) is True
    assert service.list_profiles() == []


def test_speaker_profile_rejects_invalid_or_duplicate_names_and_mapping():
    service = SpeechSpeakerProfilesService(FakeDb())
    service.create_profile("Podcast", {"SPEAKER_00": "Host"})
    with pytest.raises(ValueError, match="existe"):
        service.create_profile(" podcast ", {"SPEAKER_00": "Outro"})
    with pytest.raises(ValueError, match="SPEAKER"):
        service.create_profile("Ruim", {"speaker 0": "Nome"})
    with pytest.raises(ValueError, match="exibição"):
        service.create_profile("Vazio", {"SPEAKER_00": "   "})
