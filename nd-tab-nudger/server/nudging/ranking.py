"""
Hybrid fusion ranking — the "beyond basic similarity search" piece.

Two independent rankings over the same candidate tabs:
  1. staleness  — oldest `openedAt` first (simple, no vector query)
  2. semantic   — nearest to a fixed "actionable task" anchor vector
                  (query_tabs against the tabs collection itself)

They're fused client-side with Reciprocal Rank Fusion (RRF): each item's
score is the sum of 1/(k + rank) across the lists it appears in. This
surfaces tabs that are *both* stale and clearly actionable, rather than
just "oldest" or just "closest match" alone.
"""

from config import (
    NUDGE_CANDIDATE_LIMIT,
    NUDGE_CARD_COUNT,
    HIGH_PRESSURE_VISIT_THRESHOLD,
    ACTIONABLE_TASK_ANCHOR,
)
from ingestion.embeddings import embed_text
from nudging.session_state import get_distraction_pressure
from vectordb.client import query_tabs, scroll_all_tabs

RRF_K = 60


def _staleness_ranking(candidates):
    # Oldest openedAt first = most stale = rank 0.
    return sorted(candidates, key=lambda c: c["openedAt"])


def _semantic_ranking(candidates):
    anchor_vector = embed_text(ACTIONABLE_TASK_ANCHOR)
    results = query_tabs(anchor_vector, top_k=len(candidates))
    # results are ordered nearest-first already; map back to our candidates by tabId
    order = [r.payload["tabId"] for r in results]
    by_id = {c["tabId"]: c for c in candidates}
    return [by_id[tab_id] for tab_id in order if tab_id in by_id]


def _rrf_fuse(*rankings):
    scores = {}
    items_by_id = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            tab_id = item["tabId"]
            items_by_id[tab_id] = item
            scores[tab_id] = scores.get(tab_id, 0.0) + 1.0 / (RRF_K + rank)

    ranked_ids = sorted(scores, key=lambda tab_id: scores[tab_id], reverse=True)
    return [items_by_id[tab_id] for tab_id in ranked_ids]


def _card_count_for_pressure():
    """
    Choice overload makes ADHD task-initiation harder, not easier — so the
    more someone is actively bouncing between distraction tabs right now,
    the fewer options the nudge should show. One clear next tab beats a
    list when attention is already fragmented.
    """
    visit_count, _ = get_distraction_pressure()
    if visit_count >= HIGH_PRESSURE_VISIT_THRESHOLD:
        return 1
    return NUDGE_CARD_COUNT


def rank_nudge_candidates():
    """
    Returns (cards_candidates, all_open_tabs) where cards_candidates is the
    fused top-N non-distraction tabs, and all_open_tabs is every tracked tab
    (for the New Tab page's flat list).
    """
    points = scroll_all_tabs(limit=NUDGE_CANDIDATE_LIMIT)
    all_tabs = [p.payload for p in points]

    actionable = [t for t in all_tabs if t.get("label") != "distraction"]
    if not actionable:
        return [], all_tabs

    fused = _rrf_fuse(_staleness_ranking(actionable), _semantic_ranking(actionable))
    return fused[: _card_count_for_pressure()], all_tabs
