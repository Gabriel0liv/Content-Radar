from types import SimpleNamespace

from src.services.reference_reconciliation_service import choose_canonical_source


def make_source(source_id: int, active: int, total: int):
    transcripts = [SimpleNamespace(is_active=index < active) for index in range(total)]
    return SimpleNamespace(id=source_id, transcripts=transcripts)


def test_canonical_prefers_source_with_active_transcript():
    without_active = make_source(1, active=0, total=3)
    with_active = make_source(2, active=1, total=1)

    assert choose_canonical_source([without_active, with_active]).id == 2


def test_canonical_then_prefers_more_transcripts():
    one = make_source(1, active=0, total=1)
    three = make_source(2, active=0, total=3)

    assert choose_canonical_source([one, three]).id == 2


def test_canonical_final_tiebreaker_is_oldest_id():
    older = make_source(4, active=0, total=2)
    newer = make_source(9, active=0, total=2)

    assert choose_canonical_source([newer, older]).id == 4
