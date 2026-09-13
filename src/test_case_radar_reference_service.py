from types import SimpleNamespace

import pytest

from src.services.case_radar_reference_service import CaseRadarReferenceError, CaseRadarReferenceService


class FakeDb:
    def __init__(self, sources):
        self.sources = sources
        self.added = []
        self.commits = 0

    def get(self, model, key):
        return self.sources.get(key)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def refresh(self, value):
        return None


class FakeReferences:
    def __init__(self):
        self.reference = None
        self.created_source_payload = None
        self.jobs = []
        self.created_jobs = 0
        self.transcripts = []
        self.segments = []

    def get_reference_source_by_id(self, source_id):
        if self.reference and self.reference.id == source_id:
            return self.reference
        return None

    def get_reference_source_by_youtube_video_id(self, video_id):
        if self.reference and self.reference.youtube_video_id == video_id:
            return self.reference
        return None

    def create_reference_source(self, payload):
        self.created_source_payload = payload
        self.reference = SimpleNamespace(
            id=20,
            source_type="youtube_video",
            source_url=payload.source_url,
            youtube_video_id=payload.youtube_video_id,
        )
        return self.reference

    def list_import_jobs_by_source_id(self, source_id):
        return list(self.jobs)

    def create_import_job(self, source_url, preferred_languages, method):
        self.created_jobs += 1
        job = SimpleNamespace(
            id=30,
            reference_source_id=None,
            source_url=source_url,
            preferred_languages=preferred_languages,
            method=method,
            status="queued",
        )
        self.jobs.insert(0, job)
        return job

    def save_import_job(self, job):
        return job

    def list_transcripts_by_source(self, source_id):
        return self.transcripts

    def list_segments_by_transcript_id(self, transcript_id):
        return self.segments


def _youtube_source(**overrides):
    data = {
        "id": 1,
        "platform": "youtube",
        "external_id": "abcdefghijk",
        "canonical_url": "https://youtube.com/watch?v=abcdefghijk",
        "reference_source_id": None,
        "title_or_caption": "Mystery video",
        "author_display_name": "Mystery Channel",
        "author_handle": None,
        "text": "description",
        "published_at": None,
        "duration_seconds": 42.0,
        "engagement_json": {"views": 100, "likes": 10},
        "thumbnail_url": "https://img.example/x.jpg",
        "language": "en",
        "discovery_method": "official_api",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_promote_reuses_existing_youtube_reference():
    source = _youtube_source()
    db = FakeDb({1: source})
    service = CaseRadarReferenceService(db)
    refs = FakeReferences()
    refs.reference = SimpleNamespace(
        id=20,
        source_type="youtube_video",
        source_url=source.canonical_url,
        youtube_video_id="abcdefghijk",
    )
    service.references = refs

    reference = service.promote_to_reference(1)

    assert reference.id == 20
    assert refs.created_source_payload is None
    assert source.reference_source_id == 20


def test_promote_creates_youtube_reference_without_hiding_as_manual():
    source = _youtube_source()
    db = FakeDb({1: source})
    service = CaseRadarReferenceService(db)
    refs = FakeReferences()
    service.references = refs

    reference = service.promote_to_reference(1)

    assert reference.source_type == "youtube_video"
    assert refs.created_source_payload.source_type == "youtube_video"
    assert refs.created_source_payload.youtube_video_id == "abcdefghijk"
    assert source.reference_source_id == 20


def test_non_youtube_promotion_is_explicitly_rejected_until_schema_supports_it():
    source = _youtube_source(platform="x", external_id="123", canonical_url="https://x.com/u/status/123")
    db = FakeDb({1: source})
    service = CaseRadarReferenceService(db)
    service.references = FakeReferences()

    with pytest.raises(CaseRadarReferenceError):
        service.promote_to_reference(1)


def test_transcription_request_reuses_existing_nonfailed_job():
    source = _youtube_source(reference_source_id=20)
    db = FakeDb({1: source})
    service = CaseRadarReferenceService(db)
    refs = FakeReferences()
    refs.reference = SimpleNamespace(
        id=20,
        source_type="youtube_video",
        source_url=source.canonical_url,
        youtube_video_id="abcdefghijk",
    )
    existing = SimpleNamespace(id=99, status="queued")
    refs.jobs = [existing]
    service.references = refs

    result = service.request_transcription(1)

    assert result is existing
    assert refs.created_jobs == 0


def test_transcription_request_creates_linked_reference_import_job_once():
    source = _youtube_source()
    db = FakeDb({1: source})
    service = CaseRadarReferenceService(db)
    refs = FakeReferences()
    service.references = refs

    first = service.request_transcription(1)
    second = service.request_transcription(1)

    assert first is second
    assert first.reference_source_id == 20
    assert refs.created_jobs == 1


def test_existing_active_transcript_segments_are_reused_for_evidence():
    source = _youtube_source(reference_source_id=20)
    db = FakeDb({1: source})
    service = CaseRadarReferenceService(db)
    refs = FakeReferences()
    refs.reference = SimpleNamespace(
        id=20,
        source_type="youtube_video",
        source_url=source.canonical_url,
        youtube_video_id="abcdefghijk",
    )
    refs.transcripts = [SimpleNamespace(id=7, is_active=True)]
    refs.segments = [SimpleNamespace(id=70, transcript_id=7, text="fala", start_time=1.0, end_time=2.0)]
    service.references = refs

    segments = service.get_active_transcript_segments(1)

    assert segments[0].id == 70
    assert segments[0].transcript_id == 7
