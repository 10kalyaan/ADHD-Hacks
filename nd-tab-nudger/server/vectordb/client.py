"""
Shared VectorAI DB client + collection schemas.

Verified against `actian-vectorai-client` 1.0.2. Notes that cost us time
once, so they're written down:

- The pip package is `actian-vectorai-client`; the *import* is `actian_vectorai`.
- The client is gRPC. `url` is bare `host:port` — passing a `http://` scheme
  raises ValueError. Default gRPC port is 6574 (REST is 6573).
- `connect()` must be called explicitly; the `collections`/`points`
  namespaces proxy None until it is.
- `points.scroll()` returns a `(points, next_offset)` tuple, not a list.

Every other module goes through *this* file only, so an SDK change is a
one-file fix.
"""

import threading

from actian_vectorai import VectorAIClient, VectorParams, Distance

from config import VECTORAI_URL, TABS_COLLECTION, LABELS_COLLECTION, EMBEDDING_DIM

_client = None
_client_lock = threading.Lock()


def get_client():
    """Process-wide connected client. Flask's dev server is threaded, so
    creation is guarded — two concurrent /ingest calls must not race."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                client = VectorAIClient(url=VECTORAI_URL)
                client.connect()
                _client = client
    return _client


def ensure_collections():
    """Idempotent: create both collections if they don't already exist."""
    client = get_client()
    # Cosine matches OpenAI embeddings, which ship normalized.
    params = VectorParams(size=EMBEDDING_DIM, distance=Distance.Cosine)

    for name in (TABS_COLLECTION, LABELS_COLLECTION):
        client.collections.get_or_create(name, vectors_config=params)


def upsert_tab(point_id, vector, payload):
    client = get_client()
    client.points.upsert_single(TABS_COLLECTION, id=point_id, vector=vector, payload=payload)


def upsert_label_example(point_id, vector, payload):
    client = get_client()
    client.points.upsert_single(LABELS_COLLECTION, id=point_id, vector=vector, payload=payload)


def query_labels(vector, top_k):
    """Nearest label-collection neighbors for classification.
    Returns a list of ScoredPoint (`.id`, `.score`, `.payload`)."""
    client = get_client()
    return client.points.search(LABELS_COLLECTION, vector, limit=top_k)


def query_tabs(vector, top_k, filter=None):
    """Nearest tabs-collection neighbors, optionally filtered."""
    client = get_client()
    return client.points.search(TABS_COLLECTION, vector, limit=top_k, filter=filter)


def get_tab(point_id):
    """One tracked tab's payload, or None if it is not stored."""
    client = get_client()
    found = client.points.get(TABS_COLLECTION, ids=[point_id])
    return found[0].payload if found else None


def delete_tabs(point_ids):
    """Drop tracked tabs the browser has told us are closed.

    Without this the collection grows forever, and since closed tabs are the
    *oldest* they dominate the staleness ranking — the nudge would recommend
    tabs that no longer exist.
    """
    ids = list(point_ids)
    if not ids:
        return 0
    client = get_client()
    client.points.delete(TABS_COLLECTION, ids=ids, strict=False)
    return len(ids)


def scroll_all_tabs(limit=100):
    """All currently-tracked tab points (builds ranking + the open_tabs list).

    Unwraps the SDK's `(points, next_offset)` tuple and returns just the
    list of RetrievedPoint — callers want the points.
    """
    client = get_client()
    points, _next_offset = client.points.scroll(TABS_COLLECTION, limit=limit)
    return points


def recreate_collections():
    """Drop and rebuild both collections from scratch.

    Repeatedly emptying a collection can leave its HNSW index in a Red
    state where points still store and fetch by id but vector search
    silently returns fewer results — or none. `ensure_collections` uses
    get_or_create and will not repair that, so this is the escape hatch:
    `python -m ingestion.seed_labels --reset`. Destroys all tracked tabs.
    """
    client = get_client()
    params = VectorParams(size=EMBEDDING_DIM, distance=Distance.Cosine)
    for name in (TABS_COLLECTION, LABELS_COLLECTION):
        client.collections.recreate(name, vectors_config=params)
