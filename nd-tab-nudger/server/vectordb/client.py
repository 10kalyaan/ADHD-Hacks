"""
Shared VectorAI DB client + collection schemas.

Uses the `actian-vectorai-client` SDK. The exact method names below
(`create_collection`, `upsert`, `query`) follow the SDK's documented
client pattern (host/port constructor, collection-scoped CRUD + KNN
query returning (id, score, payload) tuples) — double-check against
whatever version is installed via `pip show actian-vectorai-client` and
adjust call sites here if a method signature differs. Every other module
in this project goes through *this* file only, so a version mismatch is
a one-file fix.
"""

from actian_vectorai_client import VectorAIClient

from config import VECTORAI_HOST, TABS_COLLECTION, LABELS_COLLECTION, EMBEDDING_DIM

_client = None


def get_client():
    global _client
    if _client is None:
        _client = VectorAIClient(host=VECTORAI_HOST)
    return _client


def ensure_collections():
    """Idempotent: create both collections if they don't already exist."""
    client = get_client()
    existing = {c.name for c in client.list_collections()}

    if TABS_COLLECTION not in existing:
        client.create_collection(name=TABS_COLLECTION, dimension=EMBEDDING_DIM)

    if LABELS_COLLECTION not in existing:
        client.create_collection(name=LABELS_COLLECTION, dimension=EMBEDDING_DIM)


def upsert_tab(point_id, vector, payload):
    client = get_client()
    client.collection(TABS_COLLECTION).upsert(id=point_id, vector=vector, payload=payload)


def upsert_label_example(point_id, vector, payload):
    client = get_client()
    client.collection(LABELS_COLLECTION).upsert(id=point_id, vector=vector, payload=payload)


def query_labels(vector, top_k):
    """Returns nearest label-collection neighbors for classification."""
    client = get_client()
    return client.collection(LABELS_COLLECTION).query(vector=vector, top_k=top_k)


def query_tabs(vector, top_k, filter=None):
    """Returns nearest tabs-collection neighbors, optionally filtered."""
    client = get_client()
    return client.collection(TABS_COLLECTION).query(vector=vector, top_k=top_k, filter=filter)


def scroll_all_tabs(limit=100):
    """Fetch all currently-tracked tab points (used to build ranking + open_tabs list)."""
    client = get_client()
    return client.collection(TABS_COLLECTION).scroll(limit=limit)
