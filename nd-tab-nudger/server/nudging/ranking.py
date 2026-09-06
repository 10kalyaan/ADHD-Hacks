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
    MAX_TRACKED_TABS,
    LABEL_CHILL,
)
from ingestion.embeddings import embed_text
from nudging.session_state import get_distraction_pressure
from vectordb.client import query_tabs, scroll_all_tabs

RRF_K = 60


def _staleness_ranking(candidates):
    # Oldest openedAt first = most stale = rank 0.
    return sorted(candidates, key=lambda c: c["openedAt"])


def _semantic_ranking(candidates, search_k):
    anchor_vector = embed_text(ACTIONABLE_TASK_ANCHOR)
    # Search the whole tracked set, not just len(candidates). The collection
    # also holds chill tabs, and asking for only len(candidates) lets
    # them take the top slots — candidates then fall out of the result set
    # entirely and RRF silently degrades into staleness-only ranking.
    results = query_tabs(anchor_vector, top_k=search_k)
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


def _spread_labels(ranked, count):
    """Pick `count` cards, preferring a different label for each.

    Two work tabs say less than one work tab and one sidequest -- picking
    strictly by score tends to return a run of whichever label happens to
    dominate the open set, so a sidequest never surfaces. Falls back to plain
    rank order once the labels run out.
    """
    picked, seen = [], set()
    for item in ranked:
        if len(picked) == count:
            break
        label = item.get("label")
        if label not in seen:
            picked.append(item)
            seen.add(label)

    if len(picked) < count:
        chosen = {id(p) for p in picked}
        picked += [i for i in ranked if id(i) not in chosen][: count - len(picked)]
        # Keep the fused ordering rather than the order they were topped up in.
        picked.sort(key=ranked.index)

    return picked


def rank_nudge_candidates():
    """
    Returns (cards_candidates, all_open_tabs) where cards_candidates is the
    fused top-N non-chill tabs, and all_open_tabs is every tracked tab
    (for the New Tab page's flat list).
    """
    # Read the whole tracked set. Scrolling only NUDGE_CANDIDATE_LIMIT here
    # was pinning the New Tab page's "tabs open" tile at 20 no matter how many
    # tabs were actually open -- that limit bounds the ranking pool, not the DB read.
    points = scroll_all_tabs(limit=MAX_TRACKED_TABS)
    all_tabs = [p.payload for p in points]

    actionable = [t for t in all_tabs if t.get("label") != LABEL_CHILL]
    if not actionable:
        return [], all_tabs

    # Rank the stalest slice rather than everything: with hundreds of tabs the
    # fusion is dominated by noise, and the freshest ones need no nudge.
    pool = _staleness_ranking(actionable)[:NUDGE_CANDIDATE_LIMIT]

    fused = _rrf_fuse(_staleness_ranking(pool), _semantic_ranking(pool, len(all_tabs)))
    return _spread_labels(fused, _card_count_for_pressure()), all_tabs
