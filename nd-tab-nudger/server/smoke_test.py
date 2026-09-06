"""
Offline smoke test for the DB layer + classifier.

Uses deterministic fake vectors, so it needs a running VectorAI DB but
*no* OpenAI key and no credits. Run it after `docker compose up -d` to
confirm the whole storage/classification path works before wiring in the
extension:

    python smoke_test.py

Cleans up after itself — the points it writes are deleted at the end.
"""

import random
import sys
import uuid

from config import EMBEDDING_DIM, TABS_COLLECTION, LABELS_COLLECTION
from ingestion.classifier import classify_title
from vectordb.client import (
    ensure_collections,
    get_client,
    query_labels,
    query_tabs,
    scroll_all_tabs,
    upsert_label_example,
    upsert_tab,
)

# Ids namespaced away from the real seed set so a failed run can never
# corrupt seeded label examples.
_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "nd-tab-nudger.smoketest")
TEST_TAB_IDS = [990001, 990002]
TEST_LABEL_IDS = []


def vec(seed):
    """Deterministic pseudo-vector — stands in for a real embedding."""
    rng = random.Random(seed)
    return [rng.uniform(-1, 1) for _ in range(EMBEDDING_DIM)]


def near(seed, jitter=0.02):
    """A vector close to vec(seed), so KNN should rank it as a neighbor."""
    rng = random.Random(seed * 7919)
    return [v + rng.uniform(-jitter, jitter) for v in vec(seed)]


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    # ASCII only: the Windows console is cp1252 and mangles fancy dashes.
    print(f"  [{status}] {label}{(' - ' + detail) if detail else ''}")
    return condition


def main():
    results = []

    print("1. connect + ensure_collections (idempotent)")
    ensure_collections()
    ensure_collections()
    names = get_client().collections.list()
    results.append(check("both collections exist", TABS_COLLECTION in names and LABELS_COLLECTION in names, str(names)))

    print("2. seed label examples")
    # Two well-separated clusters, each at least CLASSIFY_TOP_K big, so the
    # top-k around either one is genuinely local — with fewer points than k
    # the vote just returns whichever label is globally most common.
    plan = [("work", 1)] * 5 + [("chill", 2)] * 5
    for i, (lab, base) in enumerate(plan):
        pid = str(uuid.uuid5(_NS, f"label-{i}"))
        TEST_LABEL_IDS.append(pid)
        upsert_label_example(point_id=pid, vector=near(base), payload={"label": lab, "text": f"example {i}"})
    results.append(check("upserted label examples", True, f"{len(plan)} points"))

    print("3. query_labels returns scored points with payloads")
    hits = query_labels(vec(1), top_k=5)
    results.append(check("returns results", len(hits) > 0, f"len={len(hits)}"))
    results.append(check("hits carry .score and .payload['label']",
                         hasattr(hits[0], "score") and "label" in (hits[0].payload or {})))

    print("4. classifier majority vote")
    got = classify_title(vec(1))
    results.append(check("vector near the 'work' cluster classifies as work", got == "work", f"got '{got}'"))
    got2 = classify_title(vec(2))
    results.append(check("vector near the 'chill' cluster classifies as chill",
                         got2 == "chill", f"got '{got2}'"))

    print("5. tab storage")
    for tid in TEST_TAB_IDS:
        upsert_tab(point_id=tid, vector=vec(tid), payload={
            "tabId": tid, "title": f"tab {tid}", "url": "https://example.com",
            "domain": "example.com", "openedAt": 1730000000000, "label": "work",
        })
    stored = {p.id for p in scroll_all_tabs(limit=200)}
    results.append(check("scroll_all_tabs returns a list of points",
                         isinstance(scroll_all_tabs(limit=1), list)))
    results.append(check("both test tabs stored", all(t in stored for t in TEST_TAB_IDS)))

    print("6. upsert is idempotent (same id does not duplicate)")
    before = len(scroll_all_tabs(limit=200))
    upsert_tab(point_id=TEST_TAB_IDS[0], vector=vec(TEST_TAB_IDS[0]), payload={
        "tabId": TEST_TAB_IDS[0], "title": "changed", "url": "", "domain": "",
        "openedAt": 1, "label": "work",
    })
    after = len(scroll_all_tabs(limit=200))
    results.append(check("count unchanged after re-upsert", before == after, f"{before} -> {after}"))

    print("7. query_tabs")
    qt = query_tabs(vec(TEST_TAB_IDS[1]), top_k=1)
    results.append(check("nearest tab is the one we asked for",
                         len(qt) == 1 and qt[0].id == TEST_TAB_IDS[1]))

    print("8. cleanup")
    points = get_client().points
    points.delete(TABS_COLLECTION, ids=TEST_TAB_IDS, strict=False)
    points.delete(LABELS_COLLECTION, ids=TEST_LABEL_IDS, strict=False)
    leftover = {p.id for p in scroll_all_tabs(limit=200)} & set(TEST_TAB_IDS)
    results.append(check("test points removed", not leftover, str(leftover)))

    passed, total = sum(results), len(results)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
