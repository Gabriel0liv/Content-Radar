from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

from src.case_radar.providers.base import ProviderError
from src.case_radar.providers.registry import build_default_registry
from src.schemas.case_radar import CaseResearchCreate


PLATFORMS = ("web", "youtube", "reddit", "x", "tiktok", "instagram")


def _safe_record(provider, *, status: str, results: int = 0, comments: int = 0, error_code: str | None = None):
    return {
        "platform": provider.platform,
        "method": provider.method,
        "provider": provider.name,
        "status": status,
        "results": results,
        "comments": comments,
        "error_code": error_code,
        "capabilities": provider.capabilities.model_dump(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke real dos providers configurados do Case Radar")
    parser.add_argument("--query", default="unexplained footage original source")
    parser.add_argument("--language", default="en")
    parser.add_argument("--capabilities-only", action="store_true")
    args = parser.parse_args()

    registry = build_default_registry()
    request = CaseResearchCreate(
        theme=args.query,
        desired_usable_cases=1,
        languages=[args.language],
        platforms=list(PLATFORMS),
        research_depth="quick",
        global_result_budget=30,
    )
    query = SimpleNamespace(
        query_text=args.query,
        language=args.language,
        intent="smoke",
    )

    records = []
    configured_failures = 0
    successes = 0

    for platform in PLATFORMS:
        for method in registry.methods_for(platform):
            provider = registry.get(platform, method)
            if provider is None:
                continue
            try:
                available = bool(provider.is_available())
            except Exception:
                available = False
            if not provider.capabilities.search_supported or not available:
                records.append(_safe_record(provider, status="skipped"))
                continue
            if args.capabilities_only:
                records.append(_safe_record(provider, status="available"))
                continue

            try:
                page = provider.search(request, query, cursor=None)
                comment_count = 0
                if page.candidates and provider.capabilities.comments_supported:
                    social = provider.fetch_social_context(
                        page.candidates[0],
                        {"max_comments": 3, "max_depth": 1},
                    )
                    comment_count = len(social.items)
                records.append(
                    _safe_record(
                        provider,
                        status="ok",
                        results=len(page.candidates),
                        comments=comment_count,
                    )
                )
                successes += 1
            except ProviderError as exc:
                records.append(_safe_record(provider, status="failed", error_code=exc.code))
                configured_failures += 1
            except Exception:
                # Deliberately omit exception text: third-party clients can include
                # session/cookie/token details in their raw error messages.
                records.append(_safe_record(provider, status="failed", error_code="unexpected_error"))
                configured_failures += 1

    print(json.dumps({"providers": records}, ensure_ascii=False, indent=2))
    if args.capabilities_only:
        return 0
    if configured_failures:
        return 2
    return 0 if successes else 3


if __name__ == "__main__":
    raise SystemExit(main())
