from src.case_radar.query_generator import generate_queries
from src.schemas.case_radar import CaseResearchCreate


def test_query_generation_is_deterministic():
    request = CaseResearchCreate(theme="vídeo estranho floresta", languages=["pt", "en"])
    assert generate_queries(request) == generate_queries(request)


def test_balanced_generates_all_intents_for_pt_en_es():
    request = CaseResearchCreate(
        theme="vídeo estranho floresta",
        languages=["pt", "en", "es"],
        research_depth="balanced",
    )
    queries = generate_queries(request)
    intents_by_language = {}
    for query in queries:
        intents_by_language.setdefault(query.language, set()).add(query.intent)

    expected = {"core", "source_hunt", "context", "debunk", "local_language"}
    assert intents_by_language == {"pt": expected, "en": expected, "es": expected}


def test_queries_are_deduplicated_by_normalized_text():
    request = CaseResearchCreate(theme="same", languages=["pt", "en", "es"], research_depth="balanced")
    queries = generate_queries(request)
    normalized = [" ".join(query.query_text.casefold().split()) for query in queries]
    assert len(normalized) == len(set(normalized))


def test_include_terms_are_applied_to_at_least_one_query():
    request = CaseResearchCreate(
        theme="criatura na floresta",
        include_terms=["trail camera", "night footage"],
        languages=["en"],
    )
    queries = generate_queries(request)
    assert any("trail camera" in query.query_text and "night footage" in query.query_text for query in queries)


def test_exclude_terms_are_not_injected_into_query_text():
    request = CaseResearchCreate(
        theme="criatura na floresta",
        exclude_terms=["ARG", "staged"],
        languages=["en"],
    )
    queries = generate_queries(request)
    assert all("ARG" not in query.query_text and "staged" not in query.query_text for query in queries)


def test_depth_controls_number_of_variants():
    quick = generate_queries(CaseResearchCreate(theme="caso", languages=["pt"], research_depth="quick"))
    balanced = generate_queries(CaseResearchCreate(theme="caso", languages=["pt"], research_depth="balanced"))
    deep = generate_queries(CaseResearchCreate(theme="caso", languages=["pt"], research_depth="deep"))

    assert len(quick) < len(balanced) < len(deep)


def test_generated_queries_preserve_requested_platform_targets():
    request = CaseResearchCreate(
        theme="caso estranho",
        languages=["pt"],
        platforms=["youtube", "reddit"],
    )
    queries = generate_queries(request)
    assert all(query.target_platforms == ("youtube", "reddit") for query in queries)
