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


def scroll_all_tabs(limit=100):
    """All currently-tracked tab points (builds ranking + the open_tabs list).

    Unwraps the SDK's `(points, next_offset)` tuple and returns just the
    list of RetrievedPoint — callers want the points.
    """
    client = get_client()
    points, _next_offset = client.points.scroll(TABS_COLLECTION, limit=limit)
    return points
