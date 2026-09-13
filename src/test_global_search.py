from src.services.global_search_service import build_excerpt, text_rank


def test_exact_title_match_outranks_body_only_match():
    exact = text_rank("minecraft", "Minecraft", "")
    body = text_rank("minecraft", "A strange video", "This was made inside Minecraft")
    assert exact > body


def test_title_prefix_outranks_title_contains():
    prefix = text_rank("mine", "Minecraft horror", "")
    contains = text_rank("mine", "The best Minecraft series", "")
    assert prefix > contains


def test_transcript_excerpt_keeps_match_context():
    text = "Before this we explored the house. Then the creeper destroyed the redstone door and everyone ran away. After that we returned home."
    excerpt = build_excerpt(text, "redstone", max_chars=80)
    assert "redstone" in excerpt.lower()
    assert len(excerpt) <= 83
