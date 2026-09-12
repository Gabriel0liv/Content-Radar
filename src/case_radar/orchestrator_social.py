from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from src.case_radar.orchestrator import CaseRadarOrchestrator
from src.case_radar.types import Candidate
from src.case_radar.url_normalization import canonicalize_url, infer_platform_from_url
from src.models.case_radar import CaseSource, ResearchSource, SocialContextItem


class SocialResearchOrchestrator(CaseRadarOrchestrator):
    """Case Radar orchestrator with recursive source promotion from social context.

    URLs mentioned in useful comments/replies become auxiliary ResearchSource rows of
    the same case. They are not clustered as independent cases merely because a
    comment linked to them.
    """

    @staticmethod
    def _external_id_from_url(platform: str, url: str) -> str | None:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if platform == "x" and "status" in parts:
            index = parts.index("status")
            return parts[index + 1] if index + 1 < len(parts) else None
        if platform == "tiktok" and "video" in parts:
            index = parts.index("video")
            return parts[index + 1] if index + 1 < len(parts) else None
        if platform == "instagram" and len(parts) >= 2 and parts[0] in {"p", "reel", "reels", "tv"}:
            return parts[1]
        if platform == "youtube" and parsed.path == "/watch":
            return (parse_qs(parsed.query).get("v") or [None])[0]
        return None

    @staticmethod
    def _role_for_social(item: SocialContextItem) -> tuple[str, float, str]:
        categories = set(getattr(item, "categories_json", None) or [])
        if "debunk" in categories or "technical_explanation" in categories:
            return (
                "debunk",
                0.35,
                "URL citada em comentário/resposta como explicação ou debunk.",
            )
        if "origin" in categories:
            return (
                "original_candidate",
                0.45,
                "URL citada em comentário/resposta classificada como pista de origem.",
            )
        return (
            "context",
            0.30,
            "URL citada em comentário/resposta como fonte de contexto.",
        )

    def _case_id_for_sources(self, sources: list[ResearchSource]) -> int | None:
        source_ids = [int(source.id) for source in sources if getattr(source, "id", None) is not None]
        if not source_ids:
            return None
        values = list(
            self.db.execute(
                select(CaseSource.case_id)
                .where(CaseSource.source_id.in_(source_ids))
                .order_by(CaseSource.id.asc())
            ).scalars()
        )
        return int(values[0]) if values else None

    def _try_enrich_promoted(self, source: ResearchSource) -> ResearchSource:
        parsed_external_id = self._external_id_from_url(source.platform, source.canonical_url)
        fetch_candidate = Candidate(
            platform=source.platform,
            external_id=parsed_external_id,
            canonical_url=source.canonical_url,
            author_handle=source.author_handle,
            author_display_name=source.author_display_name,
            title_or_caption=source.title_or_caption,
            text=source.text,
            published_at=source.published_at,
            media_type=source.media_type,
            thumbnail_url=source.thumbnail_url,
            duration_seconds=source.duration_seconds,
            language=source.language,
            engagement=source.engagement_json or {},
            hashtags=source.hashtags_json or [],
            relation=source.relation_json,
            discovery_query=f"social-source:{source.id}",
            discovery_method="social_link",
            raw_json=source.raw_json or {},
            source_confidence=float(source.source_confidence or 0.0),
        )
        for method in self.registry.methods_for(source.platform):
            provider = self.registry.get(source.platform, method)
            if provider is None or not provider.capabilities.source_fetch_supported:
                continue
            try:
                if not provider.is_available():
                    continue
                snapshot = provider.fetch_source(fetch_candidate)
            except Exception:
                continue
            # Keep the row URL-keyed. A previously discovered URL may not yet have an
            # external id, and switching the upsert key here could violate uq_run_url.
            enriched = snapshot.candidate.model_copy(
                update={
                    "external_id": None,
                    "canonical_url": source.canonical_url,
                    "relation": {
                        **(snapshot.candidate.relation or {}),
                        **(source.relation_json or {}),
                        "resolved_external_id": snapshot.candidate.external_id or parsed_external_id,
                    },
                }
            )
            return self.repo.upsert_source(enriched, source.run_id, source.query_id)
        return source

    def _promote_social_url(
        self,
        *,
        case_id: int,
        origin_source: ResearchSource,
        item: SocialContextItem,
        url: str,
    ) -> ResearchSource | None:
        try:
            canonical = canonicalize_url(str(url))
        except Exception:
            return None
        if not canonical or canonical == canonicalize_url(origin_source.canonical_url):
            return None

        platform = infer_platform_from_url(canonical)
        role, confidence, reason = self._role_for_social(item)
        candidate = Candidate(
            platform=platform,
            external_id=None,
            canonical_url=canonical,
            title_or_caption=None,
            text=None,
            relation={
                "linked_from_source_id": int(origin_source.id),
                "social_context_item_id": int(item.id),
                "url_external_id": self._external_id_from_url(platform, canonical),
            },
            discovery_query=f"social-context:{item.id}",
            discovery_method="social_link",
            raw_json={
                "promoted_from_social_context": True,
                "social_context_item_id": int(item.id),
            },
            source_confidence=confidence,
        )
        promoted = self.repo.upsert_source(candidate, origin_source.run_id, None)
        self.repo.link_case_source(
            case_id=case_id,
            source_id=promoted.id,
            role=role,
            provenance_confidence=confidence,
            reason=reason,
            evidence_json={
                "social_context_item_id": int(item.id),
                "source_id": int(origin_source.id),
            },
        )
        return self._try_enrich_promoted(promoted)

    def _social_link_targets(
        self,
        sources: list[ResearchSource],
        social: list[SocialContextItem],
    ) -> dict[int, set[int]]:
        targets = super()._social_link_targets(sources, social)
        case_id = self._case_id_for_sources(sources)
        if case_id is None:
            return targets

        by_id = {int(source.id): source for source in sources if getattr(source, "id", None) is not None}
        by_url: dict[str, ResearchSource] = {}
        for source in sources:
            try:
                by_url[canonicalize_url(source.canonical_url)] = source
            except Exception:
                continue

        for item in social:
            origin_source = by_id.get(int(item.source_id))
            if origin_source is None:
                continue
            for raw_url in item.urls_json or []:
                try:
                    canonical = canonicalize_url(str(raw_url))
                except Exception:
                    continue
                existing = by_url.get(canonical)
                if existing is not None:
                    if existing.id != origin_source.id:
                        targets.setdefault(int(origin_source.id), set()).add(int(existing.id))
                    continue
                promoted = self._promote_social_url(
                    case_id=case_id,
                    origin_source=origin_source,
                    item=item,
                    url=canonical,
                )
                if promoted is None:
                    continue
                if all(int(source.id) != int(promoted.id) for source in sources):
                    sources.append(promoted)
                by_id[int(promoted.id)] = promoted
                by_url[canonicalize_url(promoted.canonical_url)] = promoted
                targets.setdefault(int(origin_source.id), set()).add(int(promoted.id))
                targets.setdefault(int(promoted.id), set())
        return targets
