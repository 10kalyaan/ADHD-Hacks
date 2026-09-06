from collections import Counter

from config import CLASSIFY_TOP_K, LABEL_SIDEQUEST
from vectordb.client import query_labels


def classify_title(vector):
    """
    KNN majority vote against the `labels` seed collection.
    Each neighbor's payload carries a `label` field (work/sidequest/chill);
    the most common label among the top-k nearest wins ties broken by nearest
    neighbor.
    """
    neighbors = query_labels(vector, top_k=CLASSIFY_TOP_K)
    if not neighbors:
        return LABEL_SIDEQUEST  # safe default, never crash ingestion over this

    labels = [n.payload["label"] for n in neighbors]
    counts = Counter(labels)
    top_count = max(counts.values())
    tied = [label for label, count in counts.items() if count == top_count]

    if len(tied) == 1:
        return tied[0]

    # Tie: fall back to the single nearest neighbor's label.
    return labels[0]
