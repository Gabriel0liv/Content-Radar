from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import select

from src.case_radar.clustering import compare_sources
from src.case_radar.dossier import build_factual_dossier
from src.case_radar.provenance import ProvenanceSource, resolve_provenance
from src.case_radar.providers.base import ProviderBudget, ProviderUnavailable
from src.case_radar.providers.registry import ProviderRegistry
from src.case_radar.query_generator import generate_queries
from src.case_radar.social_context import classify_social_item, score_social_item
from src.case_radar.types import Candidate
from src.case_radar.url_normalization import canonicalize_url
from src.models.case_radar import (
    CaseClaim,
    CaseEvidence,
    CaseResearchQuery,
    CaseSource,
    ResearchCase,
    ResearchSource,
    SocialContextItem,
)
from src.repositories.case_radar import CaseRadarRepository
from src.schemas.case_radar import CaseResearchCreate


class CaseRadarCancelled(RuntimeError):
    pass


@dataclass(frozen=True)
class OrchestratorResult:
    partial: bool
    summary: dict[str, Any]


class CaseRadarOrchestrator:
    STAGES = (
        ("generating_queries", 5),
        ("discovering", 15),
        ("enriching_sources", 35),
        ("collecting_social_context", 50),
        ("clustering_cases", 65),
        ("researching_cases", 80),
        ("finalizing", 95),
    )

    CASE_SEED_INTENTS = frozenset({"core", "local_language"})

    SOCIAL_CLAIM_PRIORITY = (
        "debunk",
        "technical_explanation",
        "correction",
        "origin",
        "context",
        "author_response",
        "witness_claim",
        "link",
    )

    def __init__(self, repo: CaseRadarRepository, registry: ProviderRegistry) -> None:
        self.repo = repo
        self.db = repo.db
        self.registry = registry

    @staticmethod
    def _check_cancel(cancel_check: Callable[[], bool]) -> None:
        if cancel_check():
            raise CaseRadarCancelled("Pesquisa cancelada")

    @classmethod
    def _can_seed_case(cls, source: ResearchSource | Any) -> bool:
        query = getattr(source, "query", None)
        intent = getattr(query, "intent", None)
        return intent in cls.CASE_SEED_INTENTS

    @classmethod
    def _group_priority(cls, group: list[ResearchSource]) -> tuple[int, int, float, int, int]:
        source_count = len(group)
        platforms = len({getattr(source, "platform", None) for source in group if getattr(source, "platform", None)})
        confidence = max((float(getattr(source, "source_confidence", 0.0) or 0.0) for source in group), default=0.0)
        seed_count = sum(1 for source in group if cls._can_seed_case(source))
        first_id = min((int(getattr(source, "id", 0) or 0) for source in group), default=0)
        return (source_count, platforms, confidence, seed_count, -first_id)

    @staticmethod
    def _candidate_from_source(source: ResearchSource) -> Candidate:
        return Candidate(
            platform=source.platform,
            external_id=source.external_id,
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
            discovery_query=(source.query.query_text if source.query is not None else source.title_or_caption or "source"),
            discovery_method=source.discovery_method,
            raw_json=source.raw_json or {},
            source_confidence=float(source.source_confidence or 0.0),
        )

    @staticmethod
    def _budget_for(request: CaseResearchCreate, platform: str) -> ProviderBudget:
        configured = int(request.provider_budgets.get(platform, 0) or 0)
        if configured <= 0:
            divisor = max(1, len(request.platforms))
            configured = max(5, request.global_result_budget // divisor)
        request_limit = max(3, min(100, configured))
        return ProviderBudget(request_limit=request_limit, result_limit=configured)

    def _progress(self, callback: Callable[[str, int, str], None], stage: str, pct: int, message: str) -> None:
        callback(stage, pct, message)

    def _persist_queries(self, run_id: int, request: CaseResearchCreate) -> list[CaseResearchQuery]:
        generated = generate_queries(request)
        persisted: list[CaseResearchQuery] = []
        for query in generated:
            for platform in query.target_platforms:
                persisted.append(
                    self.repo.upsert_query(
                        run_id=run_id,
                        language=query.language,
                        target_platform=platform,
                        query_text=query.query_text,
                        intent=query.intent,
                        status="queued",
                    )
                )
        return persisted

    def _discover(
        self,
        run_id: int,
        request: CaseResearchCreate,
        queries: list[CaseResearchQuery],
        cancel_check: Callable[[], bool],
    ) -> tuple[list[ResearchSource], dict[str, Any], list[dict[str, Any]]]:
        budgets = {platform: self._budget_for(request, platform) for platform in request.platforms}
        coverage: dict[str, Any] = {
            platform: {"queries": 0, "results": 0, "methods": [], "errors": []}
            for platform in request.platforms
        }
        run_errors: list[dict[str, Any]] = []

        for query in queries:
            self._check_cancel(cancel_check)
            platform = query.target_platform
            if platform not in budgets:
                query.status = "skipped"
                self.db.commit()
                continue
            query.status = "running"
            self.db.commit()
            coverage[platform]["queries"] += 1
            outcome = self.registry.search_with_fallback(
                platform,
                request,
                query,
                budgets[platform],
            )
            coverage[platform]["errors"].extend(outcome.errors)
            if outcome.provider_name and outcome.provider_name not in coverage[platform]["methods"]:
                coverage[platform]["methods"].append(outcome.provider_name)
            if outcome.page is None:
                query.status = "failed"
                query.error_message = (outcome.errors[-1]["message"] if outcome.errors else "Nenhum provider disponível")
                self.db.commit()
                run_errors.extend({"platform": platform, **error} for error in outcome.errors)
                continue
            query.status = "completed"
            query.result_count = len(outcome.page.candidates)
            query.error_message = None
            coverage[platform]["results"] += len(outcome.page.candidates)
            self.db.commit()
            for candidate in outcome.page.candidates:
                self.repo.upsert_source(candidate, run_id, query.id)

        sources = self.repo.list_sources(run_id)
        return sources, coverage, run_errors

    def _enrich_sources(self, sources: list[ResearchSource], cancel_check: Callable[[], bool]) -> None:
        for source in sources:
            self._check_cancel(cancel_check)
            provider = self.registry.get(source.platform, source.discovery_method)
            if provider is None or not provider.capabilities.source_fetch_supported:
                continue
            try:
                snapshot = provider.fetch_source(self._candidate_from_source(source))
            except ProviderUnavailable:
                continue
            except Exception:
                continue
            self.repo.upsert_source(snapshot.candidate, source.run_id, source.query_id)

    def _collect_social_context(self, sources: list[ResearchSource], request: CaseResearchCreate, cancel_check: Callable[[], bool]) -> None:
        comment_limit = {"quick": 20, "balanced": 60, "deep": 150}[request.research_depth]
        depth_limit = {"quick": 2, "balanced": 4, "deep": 8}[request.research_depth]
        for source in sources:
            self._check_cancel(cancel_check)
            provider = self.registry.get(source.platform, source.discovery_method)
            if provider is None or not provider.capabilities.comments_supported:
                continue
            try:
                page = provider.fetch_social_context(
                    self._candidate_from_source(source),
                    {"max_comments": comment_limit, "max_depth": depth_limit},
                )
            except Exception:
                continue
            parent_rows: dict[str, SocialContextItem] = {}
            for item in list(page.items):
                parent_db_id = None
                if item.parent_id:
                    parent = parent_rows.get(item.parent_id) or parent_rows.get(item.parent_id.removeprefix("t1_"))
                    if parent is not None:
                        parent_db_id = parent.id
                categories = sorted(
                    classify_social_item(
                        item.body,
                        author_reply=item.author_reply,
                        pinned=item.pinned,
                    )
                )
                row = self.repo.create_social_item(
                    source_id=source.id,
                    platform_item_id=item.platform_item_id,
                    parent_social_context_id=parent_db_id,
                    author_handle=item.author_handle,
                    author_display_name=item.author_display_name,
                    body=item.body,
                    published_at=item.published_at,
                    engagement_json=item.engagement,
                    pinned=item.pinned,
                    author_reply=item.author_reply,
                    urls_json=item.external_links,
                    categories_json=categories,
                    usefulness_score=score_social_item(item),
                    raw_json=item.raw_json,
                )
                if item.platform_item_id:
                    parent_rows[item.platform_item_id] = row
                    parent_rows[f"t1_{item.platform_item_id}"] = row

    def _existing_case_by_source(self, run_id: int) -> dict[int, ResearchCase]:
        rows = self.db.execute(
            select(CaseSource, ResearchCase)
            .join(ResearchCase, ResearchCase.id == CaseSource.case_id)
            .where(ResearchCase.run_id == run_id)
        ).all()
        return {int(link.source_id): case for link, case in rows}

    def _cluster(
        self,
        run_id: int,
        sources: list[ResearchSource],
        *,
        max_cases: int | None = None,
    ) -> list[ResearchCase]:
        parent = {source.id: source.id for source in sources}

        def find(value: int) -> int:
            while parent[value] != value:
                parent[value] = parent[parent[value]]
                value = parent[value]
            return value

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)

        for index, left in enumerate(sources):
            for right in sources[index + 1 :]:
                decision = compare_sources(left, right)
                if decision.action == "merge":
                    union(left.id, right.id)

        groups: dict[int, list[ResearchSource]] = {}
        for source in sources:
            groups.setdefault(find(source.id), []).append(source)

        existing_by_source = self._existing_case_by_source(run_id)
        existing_groups: list[tuple[ResearchCase, list[ResearchSource], list[ResearchSource]]] = []
        new_groups: list[tuple[None, list[ResearchSource], list[ResearchSource]]] = []

        for group in groups.values():
            existing = [existing_by_source[source.id] for source in group if source.id in existing_by_source]
            case = min(existing, key=lambda item: item.id) if existing else None
            seed_sources = [source for source in group if self._can_seed_case(source)]
            if case is not None:
                existing_groups.append((case, group, seed_sources))
            elif seed_sources:
                new_groups.append((None, group, seed_sources))

        new_groups.sort(key=lambda item: self._group_priority(item[1]), reverse=True)
        if max_cases is not None:
            remaining = max(0, int(max_cases) - len(existing_groups))
            new_groups = new_groups[:remaining]

        cases: list[ResearchCase] = []
        selected_groups = [*existing_groups, *new_groups]
        for existing_case, group, seed_sources in selected_groups:
            case = existing_case
            if case is None:
                primary = min(
                    seed_sources,
                    key=lambda source: (source.published_at is None, source.published_at, source.id),
                )
                case = self.repo.create_case(
                    run_id=run_id,
                    provisional_title=primary.title_or_caption or primary.text or f"Caso {primary.id}",
                    normalized_summary=primary.text or primary.title_or_caption,
                    selected_primary_source_id=primary.id,
                )
            for source in group:
                self.repo.link_case_source(case_id=case.id, source_id=source.id)
            cases.append(case)
        return list({case.id: case for case in cases}.values())

    @classmethod
    def _claim_type_for_social(cls, item: SocialContextItem) -> str | None:
        categories = set(item.categories_json or [])
        for category in cls.SOCIAL_CLAIM_PRIORITY:
            if category in categories:
                return "linked_source" if category == "link" else category
        return None

    def _materialize_social_claims(self, case: ResearchCase, social: list[SocialContextItem]) -> None:
        for item in social:
            claim_type = self._claim_type_for_social(item)
            text = " ".join((item.body or "").split())
            if claim_type is None or not text:
                continue
            status = "source_claimed" if item.author_reply or claim_type == "author_response" else "unverified"
            usefulness = max(0.0, float(item.usefulness_score or 0.0))
            confidence = min(0.65 if status == "source_claimed" else 0.45, 0.2 + usefulness / 100.0)
            claim = self.repo.upsert_claim(
                case_id=case.id,
                normalized_claim_text=text,
                claim_type=claim_type,
                status=status,
                confidence=confidence,
            )
            self.repo.link_evidence(
                claim_id=claim.id,
                stance="supports",
                social_context_item_id=item.id,
                source_id=item.source_id,
                note="Pista extraída de comentário/resposta; não tratada como fato sem corroboração independente.",
            )

    def _social_link_targets(
        self,
        sources: list[ResearchSource],
        social: list[SocialContextItem],
    ) -> dict[int, set[int]]:
        url_to_source: dict[str, int] = {}
        for source in sources:
            try:
                url_to_source[canonicalize_url(source.canonical_url)] = int(source.id)
            except Exception:
                continue
        result: dict[int, set[int]] = {int(source.id): set() for source in sources}
        for item in social:
            for url in item.urls_json or []:
                try:
                    target_id = url_to_source.get(canonicalize_url(str(url)))
                except Exception:
                    target_id = None
                if target_id is not None and target_id != item.source_id:
                    result.setdefault(int(item.source_id), set()).add(target_id)
        return result

    def _research_cases(self, run_id: int, cases: list[ResearchCase], provider_coverage: dict[str, Any]) -> list[ResearchCase]:
        for case in cases:
            links = list(self.db.execute(select(CaseSource).where(CaseSource.case_id == case.id)).scalars())
            sources = [self.db.get(ResearchSource, link.source_id) for link in links]
            sources = [source for source in sources if source is not None]
            social = list(
                self.db.execute(
                    select(SocialContextItem).where(
                        SocialContextItem.source_id.in_([source.id for source in sources])
                    )
                ).scalars()
            ) if sources else []

            self._materialize_social_claims(case, social)
            social_targets = self._social_link_targets(sources, social)

            provenance_sources = []
            for source in sources:
                linked_ids: set[int] = set()
                if isinstance(source.relation_json, dict):
                    linked_ids.update(int(value) for value in source.relation_json.get("linked_source_ids") or ())
                linked_ids.update(social_targets.get(int(source.id), set()))
                provenance_sources.append(
                    ProvenanceSource(
                        source_id=source.id,
                        published_at=source.published_at,
                        platform=source.platform,
                        author_handle=source.author_handle,
                        canonical_url=source.canonical_url,
                        links_to_source_ids=tuple(sorted(linked_ids)),
                    )
                )
            provenance = resolve_provenance(provenance_sources)
            case.earliest_known_source_id = provenance.earliest_known_source_id
            case.likely_original_source_id = provenance.likely_original_source_id
            case.origin_status = provenance.origin_status
            case.origin_confidence = provenance.confidence
            dated = [source.published_at for source in sources if source.published_at is not None]
            case.earliest_known_date = min(dated) if dated else None
            context_bonus = min(0.2, sum(1 for item in social if self._claim_type_for_social(item)) * 0.02)
            case.research_confidence = min(1.0, 0.35 + (0.12 * len(sources)) + context_bonus)
            if case.status == "researching":
                case.status = "ready"

            claims = list(self.db.execute(select(CaseClaim).where(CaseClaim.case_id == case.id)).scalars())
            evidence = list(
                self.db.execute(
                    select(CaseEvidence)
                    .join_from(CaseEvidence, CaseEvidence.claim)
                    .where(CaseEvidence.claim.has(case_id=case.id))
                ).scalars()
            )
            case.dossier_json = build_factual_dossier(
                case,
                sources=sources,
                claims=claims,
                evidence=evidence,
                social_context=social,
                provider_coverage=provider_coverage,
            )
            self.db.add(case)
            self.db.commit()
            self.db.refresh(case)
        return cases

    def execute(
        self,
        run: Any,
        *,
        progress_callback: Callable[[str, int, str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> OrchestratorResult:
        progress = progress_callback or (lambda stage, pct, message: None)
        cancelled = cancel_check or (lambda: False)
        request = CaseResearchCreate.model_validate(run.request_json)

        self._check_cancel(cancelled)
        self._progress(progress, "generating_queries", 5, "Gerando consultas de pesquisa")
        queries = self._persist_queries(run.id, request)

        self._check_cancel(cancelled)
        self._progress(progress, "discovering", 15, "Descobrindo fontes")
        sources, coverage, provider_errors = self._discover(run.id, request, queries, cancelled)

        run.provider_coverage_json = coverage
        run.discovered_candidates = len(sources)
        if provider_errors:
            existing_errors = list(run.errors_json or [])
            known = {(error.get("platform"), error.get("code"), error.get("provider"), error.get("message")) for error in existing_errors}
            for error in provider_errors:
                key = (error.get("platform"), error.get("code"), error.get("provider"), error.get("message"))
                if key not in known:
                    existing_errors.append(error)
                    known.add(key)
            run.errors_json = existing_errors
        self.db.add(run)
        self.db.commit()

        self._check_cancel(cancelled)
        self._progress(progress, "enriching_sources", 35, "Enriquecendo fontes")
        self._enrich_sources(sources, cancelled)
        sources = self.repo.list_sources(run.id)

        self._check_cancel(cancelled)
        self._progress(progress, "collecting_social_context", 50, "Coletando contexto social")
        self._collect_social_context(sources, request, cancelled)

        self._check_cancel(cancelled)
        self._progress(progress, "clustering_cases", 65, "Agrupando reposts e casos")
        cases = self._cluster(run.id, sources, max_cases=request.desired_usable_cases)
        run.clustered_cases = len(cases)
        self.db.add(run)
        self.db.commit()

        self._check_cancel(cancelled)
        self._progress(progress, "researching_cases", 80, "Resolvendo proveniência, comentários e contexto")
        cases = self._research_cases(run.id, cases, coverage)

        self._check_cancel(cancelled)
        self._progress(progress, "finalizing", 95, "Finalizando dossiês")
        usable = [case for case in cases if case.status in {"ready", "approved"}]
        rejected = [case for case in cases if case.status in {"rejected", "duplicate", "already_used"}]
        run.usable_cases = len(usable)
        run.rejected_cases = len(rejected)
        self.db.add(run)
        self.db.commit()

        material_provider_failures = any(value.get("errors") for value in coverage.values())
        target_missed = len(usable) < request.desired_usable_cases
        partial = bool(usable) and (material_provider_failures or target_missed)
        summary = {
            "discovered_candidates": len(sources),
            "clustered_cases": len(cases),
            "usable_cases": len(usable),
            "rejected_cases": len(rejected),
            "desired_usable_cases": request.desired_usable_cases,
            "provider_coverage": coverage,
            "provider_errors": provider_errors,
        }
        if not usable and (provider_errors or not sources):
            summary["no_useful_output"] = True
        return OrchestratorResult(partial=partial, summary=summary)
