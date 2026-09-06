from types import SimpleNamespace

from nudging import ranking, session_state


def setup_function(_):
    session_state.reset()


def test_rrf_fuse_boosts_items_ranked_well_in_both_lists():
    a = {"tabId": 1}
    b = {"tabId": 2}
    c = {"tabId": 3}

    staleness = [a, b, c]  # a stalest
    semantic = [b, a, c]  # b closest, a second

    fused = ranking._rrf_fuse(staleness, semantic)

    # a is top-2 in both rankings; c is last in both -> a should beat c.
    assert fused[0]["tabId"] in (1, 2)
    assert fused[-1]["tabId"] == 3


def test_rrf_fuse_includes_item_present_in_only_one_ranking():
    a = {"tabId": 1}
    only_semantic = {"tabId": 9}

    fused = ranking._rrf_fuse([a], [only_semantic])
    ids = {item["tabId"] for item in fused}
    assert ids == {1, 9}


def test_card_count_drops_to_one_under_high_pressure(monkeypatch):
    monkeypatch.setattr(ranking, "HIGH_PRESSURE_VISIT_THRESHOLD", 3)
    session_state.record_distraction_visit("reddit.com")
    session_state.record_distraction_visit("reddit.com")
    session_state.record_distraction_visit("x.com")

    assert ranking._card_count_for_pressure() == 1


def test_card_count_stays_normal_below_threshold(monkeypatch):
    monkeypatch.setattr(ranking, "HIGH_PRESSURE_VISIT_THRESHOLD", 3)
    session_state.record_distraction_visit("reddit.com")

    assert ranking._card_count_for_pressure() == ranking.NUDGE_CARD_COUNT


def test_rank_nudge_candidates_excludes_chill_tabs(monkeypatch):
    all_tabs = [
        {"tabId": 1, "title": "Q3 doc", "domain": "docs.google.com",
         "openedAt": 100, "label": "work"},
        {"tabId": 2, "title": "Reddit", "domain": "reddit.com",
         "openedAt": 200, "label": "chill"},
    ]
    monkeypatch.setattr(
        ranking, "scroll_all_tabs",
        lambda limit: [SimpleNamespace(payload=t) for t in all_tabs],
    )
    monkeypatch.setattr(ranking, "embed_text", lambda text: [0.0])
    monkeypatch.setattr(
        ranking, "query_tabs",
        lambda vector, top_k: [SimpleNamespace(payload={"tabId": 1})],
    )

    cards, tabs = ranking.rank_nudge_candidates()

    assert [c["tabId"] for c in cards] == [1]
    assert len(tabs) == 2


def test_spread_labels_prefers_a_different_category_per_card():
    ranked = [
        {"tabId": 1, "label": "work"},
        {"tabId": 2, "label": "work"},
        {"tabId": 3, "label": "sidequest"},
    ]

    # Strict rank order would return two work tabs and never surface the
    # sidequest, which is the whole point of showing a second card.
    picked = ranking._spread_labels(ranked, 2)

    assert [p["tabId"] for p in picked] == [1, 3]


def test_spread_labels_falls_back_to_rank_order_when_labels_run_out():
    ranked = [
        {"tabId": 1, "label": "work"},
        {"tabId": 2, "label": "work"},
        {"tabId": 3, "label": "work"},
    ]

    picked = ranking._spread_labels(ranked, 2)

    # Only one category available -- still return two cards, in fused order.
    assert [p["tabId"] for p in picked] == [1, 2]


def test_spread_labels_handles_fewer_candidates_than_requested():
    ranked = [{"tabId": 1, "label": "work"}]
    assert ranking._spread_labels(ranked, 2) == ranked
