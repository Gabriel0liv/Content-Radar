from src.case_radar.social_context import classify_social_item, score_social_item, select_social_context
from src.case_radar.types import SocialContextRecord


def _item(item_id, body, *, parent_id=None, depth=0, score=0, author_reply=False, pinned=False):
    return SocialContextRecord(
        platform_item_id=item_id,
        parent_id=parent_id,
        depth=depth,
        body=body,
        engagement={"score": score},
        author_reply=author_reply,
        pinned=pinned,
    )


def test_useful_comment_scores_above_reaction_only():
    useful = _item("1", "Original source was posted in 2021: https://example.com/original", score=3)
    reaction = _item("2", "que medo kkk", score=500)
    assert score_social_item(useful) > score_social_item(reaction)


def test_popularity_does_not_mark_claim_as_corroborated():
    item = _item("1", "This was in Canada", score=10000)
    categories = classify_social_item(item.body)
    assert "corroborated" not in categories


def test_classifier_finds_investigative_categories():
    categories = classify_social_item(
        "Na verdade isso é de 2021. Fonte original: https://example.com. Parece reflexo da câmera.",
        author_reply=True,
    )
    assert {"link", "origin", "correction", "context", "author_response", "technical_explanation"} <= categories


def test_select_social_context_preserves_parent_chain():
    items = [
        _item("p", "Parent with basic context", depth=0),
        _item("c", "Original source: https://example.com/original", parent_id="t1_p", depth=1),
        _item("junk", "lol", score=1000),
    ]
    selected = select_social_context(items, limit=2)
    assert [entry.item.platform_item_id for entry in selected] == ["p", "c"]


def test_unresolved_question_overlap_increases_score():
    item = _item("1", "The location was near Vancouver in Canada")
    baseline = score_social_item(item)
    with_question = score_social_item(item, unresolved_questions=["Where in Canada was this recorded?"])
    assert with_question > baseline


def test_limit_zero_returns_empty_list():
    assert select_social_context([_item("1", "context")], limit=0) == []
