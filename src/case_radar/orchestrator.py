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
from src.models.case_radar import CaseEvidence, CaseResearchQuery, CaseSource, ResearchCase, ResearchSource, SocialContextItem
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

    def __init__(self, repo: CaseRadarRepository, registry: ProviderRegistry) -> None:
        self.repo = repo
        self.db = repo.db
        self.registry = registry

    @staticmethod
    def _check_cancel(cancel_check: Callable[[], bool]) -> None:
        if cancel_check():
            raise CaseRadarCancelled("Pesquisa cancelada")

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
            pending = list(page.items)
            for item in pending:
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

    def _cluster(self, run_id: int, sources: list[ResearchSource]) -> list[ResearchCase]:
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
        cases: list[ResearchCase] = []
        for group in groups.values():
            existing = [existing_by_source[source.id] for source in group if source.id in existing_by_source]
            case = min(existing, key=lambda item: item.id) if existing else None
            if case is None:
                primary = min(group, key=lambda source: (source.published_at is None, source.published_at, source.id))
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

    def _research_cases(self, run_id: int, cases: list[ResearchCase], provider_coverage: dict[str, Any]) -> list[ResearchCase]:
        for case in cases:
            links = list(
                self.db.execute(select(CaseSource).where(CaseSource.case_id == case.id)).scalars()
            )
            sources = [self.db.get(ResearchSource, link.source_id) for link in links]
            sources = [source for source in sources if source is not None]
            provenance_sources = []
            for source in sources:
                linked_ids = ()
                if isinstance(source.relation_json, dict):
                    linked_ids = tuple(source.relation_json.get("linked_source_ids") or ())
                provenance_sources.append(
                    ProvenanceSource(
                        source_id=source.id,
                        published_at=source.published_at,
                        platform=source.platform,
                        author_handle=source.author_handle,
                        canonical_url=source.canonical_url,
                        links_to_source_ids=linked_ids,
                    )
                )
            provenance = resolve_provenance(provenance_sources)
            case.earliest_known_source_id = provenance.earliest_known_source_id
            case.likely_original_source_id = provenance.likely_original_source_id
            case.origin_status = provenance.origin_status
            case.origin_confidence = provenance.confidence
            dated = [source.published_at for source in sources if source.published_at is not None]
            case.earliest_known_date = min(dated) if dated else None
            case.research_confidence = min(1.0, 0.35 + (0.12 * len(sources)))
            if case.status == "researching":
                case.status = "ready"

            claims = list(case.claims or [])
            evidence = list(
                self.db.execute(
                    select(CaseEvidence)
                    .join_from(CaseEvidence, CaseEvidence.claim)
                    .where(CaseEvidence.claim.has(case_id=case.id))
                ).scalars()
            )
            social = list(
                self.db.execute(
                    select(SocialContextItem).where(
                        SocialContextItem.source_id.in_([source.id for source in sources])
                    )
                ).scalars()
            ) if sources else []
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
            run.errors_json = existing_errors + provider_errors
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
        cases = self._cluster(run.id, sources)
        run.clustered_cases = len(cases)
        self.db.add(run)
        self.db.commit()

        self._check_cancel(cancelled)
        self._progress(progress, "researching_cases", 80, "Resolvendo proveniência e contexto")
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
