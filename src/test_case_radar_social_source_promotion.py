from types import SimpleNamespace

from src.case_radar.orchestrator_social import SocialResearchOrchestrator


class FakeDb:
    def __init__(self):
        self.links = [SimpleNamespace(case_id=22, source_id=1)]

    def execute(self, statement):
        class Result:
            def __init__(self, values):
                self.values = values

            def scalars(self):
                return self.values

        return Result(self.links)


class FakeRepo:
    def __init__(self):
        self.db = FakeDb()
        self.sources = []
        self.case_links = []

    def upsert_source(self, candidate, run_id, query_id):
        for source in self.sources:
            if source.canonical_url == candidate.canonical_url:
                return source
        source = SimpleNamespace(
            id=len(self.sources) + 2,
            run_id=run_id,
            query_id=query_id,
            platform=candidate.platform,
            canonical_url=candidate.canonical_url,
            external_id=candidate.external_id,
            discovery_method=candidate.discovery_method,
            source_confidence=candidate.source_confidence,
            title_or_caption=candidate.title_or_caption,
            text=candidate.text,
            published_at=candidate.published_at,
            author_handle=candidate.author_handle,
            author_display_name=candidate.author_display_name,
            media_type=candidate.media_type,
            thumbnail_url=candidate.thumbnail_url,
            duration_seconds=candidate.duration_seconds,
            language=candidate.language,
            engagement_json=candidate.engagement,
            hashtags_json=candidate.hashtags,
            relation_json=candidate.relation,
            raw_json=candidate.raw_json,
        )
        self.sources.append(source)
        return source

    def link_case_source(self, **payload):
        self.case_links.append(payload)
        return SimpleNamespace(id=len(self.case_links), **payload)


class FakeRegistry:
    def methods_for(self, platform):
        return []

    def get(self, platform, method):
        return None


def _origin():
    return SimpleNamespace(
        id=1,
        run_id=9,
        query_id=4,
        platform="reddit",
        canonical_url="https://reddit.com/r/test/comments/abc/post",
    )


def test_new_origin_link_is_promoted_and_linked_to_same_case():
    repo = FakeRepo()
    origin = _origin()
    orchestrator = SocialResearchOrchestrator(repo, FakeRegistry())
    social = [
        SimpleNamespace(
            id=31,
            source_id=1,
            urls_json=["https://x.com/original/status/123?utm_source=share"],
            categories_json=["origin", "link"],
            body="Original source: https://x.com/original/status/123",
        )
    ]
    sources = [origin]

    targets = orchestrator._social_link_targets(sources, social)

    assert len(sources) == 2
    promoted = sources[1]
    assert promoted.platform == "x"
    assert promoted.canonical_url == "https://x.com/original/status/123"
    assert promoted.discovery_method == "social_link"
    assert targets[1] == {promoted.id}
    assert repo.case_links == [
        {
            "case_id": 22,
            "source_id": promoted.id,
            "role": "original_candidate",
            "provenance_confidence": 0.45,
            "reason": "URL citada em comentário/resposta classificada como pista de origem.",
            "evidence_json": {"social_context_item_id": 31, "source_id": 1},
        }
    ]


def test_debunk_link_is_contextual_evidence_not_original_candidate():
    repo = FakeRepo()
    origin = _origin()
    orchestrator = SocialResearchOrchestrator(repo, FakeRegistry())
    social = [
        SimpleNamespace(
            id=32,
            source_id=1,
            urls_json=["https://example.com/debunk/article"],
            categories_json=["debunk", "link"],
            body="This was debunked here",
        )
    ]
    sources = [origin]

    orchestrator._social_link_targets(sources, social)

    promoted = sources[1]
    assert promoted.platform == "web"
    assert repo.case_links[0]["role"] == "debunk"
    assert repo.case_links[0]["provenance_confidence"] == 0.35


def test_existing_url_is_not_promoted_twice():
    repo = FakeRepo()
    origin = _origin()
    existing = SimpleNamespace(
        id=2,
        run_id=9,
        query_id=None,
        platform="x",
        canonical_url="https://x.com/original/status/123",
    )
    sources = [origin, existing]
    orchestrator = SocialResearchOrchestrator(repo, FakeRegistry())
    social = [
        SimpleNamespace(
            id=33,
            source_id=1,
            urls_json=["https://twitter.com/original/status/123?utm_source=share"],
            categories_json=["origin", "link"],
            body="Original source",
        )
    ]

    targets = orchestrator._social_link_targets(sources, social)

    assert len(sources) == 2
    assert targets[1] == {2}
    assert repo.case_links == []
