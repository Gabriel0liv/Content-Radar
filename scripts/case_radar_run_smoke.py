from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlparse

import src.db.base  # noqa: F401
from case_worker.worker import run_once
from src.case_radar.orchestrator_social import SocialResearchOrchestrator
from src.case_radar.providers.registry import build_default_registry
from src.db.session import SessionLocal
from src.repositories.case_radar import CaseRadarRepository
from src.schemas.case_radar import CaseResearchCreate
from src.services.case_radar_service import CaseRadarService


def _valid_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _validate_dossier(case) -> dict[str, object]:
    dossier = case.dossier_json or {}
    sources = dossier.get("sources") or []
    invalid_urls = [item.get("url") for item in sources if not _valid_http_url(item.get("url"))]
    claims = []
    for key in ("verified_context", "unverified_claims", "contradictions", "alternative_explanations"):
        claims.extend(dossier.get(key) or [])

    claim_statuses = sorted({str(item.get("status")) for item in claims if item.get("status")})
    return {
        "case_id": case.id,
        "title": case.provisional_title,
        "status": case.status,
        "origin_status": case.origin_status,
        "source_count": len(sources),
        "invalid_source_urls": invalid_urls,
        "claim_statuses": claim_statuses,
        "has_dossier": bool(dossier),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a small real Case Radar research smoke.")
    parser.add_argument(
        "--theme",
        default="unexplained footage",
        help="Controlled research theme used for the smoke run.",
    )
    parser.add_argument("--desired-cases", type=int, default=3)
    args = parser.parse_args()
    desired_cases = max(1, min(3, args.desired_cases))

    db = SessionLocal()
    try:
        service = CaseRadarService(db)
        request = CaseResearchCreate(
            theme=args.theme,
            desired_usable_cases=desired_cases,
            languages=["en"],
            platforms=["web", "youtube", "reddit", "x"],
            priorities=["original source", "verifiable context"],
            exclusions=["obvious staged content"],
            research_depth="quick",
            global_result_budget=20,
            provider_budgets={
                "web": 6,
                "youtube": 6,
                "reddit": 5,
                "x": 5,
            },
        )
        run = service.create_run(request)
        repo = CaseRadarRepository(db)
        orchestrator = SocialResearchOrchestrator(repo, build_default_registry())

        worked = run_once(repo, orchestrator, "case-radar-smoke", 180)
        current = repo.get_run(run.id)
        cases = repo.list_cases(run.id)
        dossier_checks = [_validate_dossier(case) for case in cases]

        payload = {
            "run_id": run.id,
            "worked": worked,
            "status": current.status if current else None,
            "stage": current.stage if current else None,
            "desired_cases": desired_cases,
            "discovered_candidates": current.discovered_candidates if current else 0,
            "clustered_cases": current.clustered_cases if current else 0,
            "usable_cases": current.usable_cases if current else 0,
            "provider_coverage": current.provider_coverage_json if current else {},
            "errors": current.errors_json if current else [],
            "cases": dossier_checks,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

        if current is None or current.status not in {"completed", "partially_completed"}:
            return 2
        if not cases:
            return 3
        if len(cases) > desired_cases or current.usable_cases > desired_cases:
            return 4
        if any(not item["has_dossier"] for item in dossier_checks):
            return 5
        if any(item["invalid_source_urls"] for item in dossier_checks):
            return 6
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
