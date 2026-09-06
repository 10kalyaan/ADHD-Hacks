"""
Seeds the `labels` collection with hand-written example titles so
classification has something to compare against. Run once after the DB
is up:

    python -m ingestion.seed_labels
"""

import uuid

from ingestion.embeddings import embed_texts
from vectordb.client import ensure_collections, upsert_label_example

# The DB only accepts a non-negative int or a UUID as a point id, so seed ids
# are derived as uuid5 — deterministic, so re-running this script overwrites
# the same points instead of piling up duplicates that skew the KNN vote.
_SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "nd-tab-nudger.labels")


def seed_point_id(index):
    return str(uuid.uuid5(_SEED_NAMESPACE, f"seed-{index}"))

SEED_EXAMPLES = [
    # work
    ("work", "Q3 planning doc - Google Docs"),
    ("work", "Sprint board - Jira"),
    ("work", "Pull request #482: fix auth timeout - GitHub"),
    ("work", "Quarterly budget spreadsheet - Google Sheets"),
    ("work", "Team standup notes - Notion"),
    ("work", "Client proposal draft - Google Docs"),
    # reference
    ("reference", "React hooks guide - reactjs.org"),
    ("reference", "How to center a div - Stack Overflow"),
    ("reference", "Python asyncio documentation"),
    ("reference", "MDN: Array.prototype.map()"),
    ("reference", "Postgres indexing best practices - blog post"),
    ("reference", "Figma API reference"),
    # distraction
    ("distraction", "Reddit - Dive into anything"),
    ("distraction", "Home / X"),
    ("distraction", "Instagram"),
    ("distraction", "YouTube - Home"),
    ("distraction", "reddit.com/r/all"),
    ("distraction", "Trending videos - YouTube"),
]


def run():
    ensure_collections()

    # One batched embedding call for all examples, not one per example.
    vectors = embed_texts([text for _label, text in SEED_EXAMPLES])

    for i, ((label, text), vector) in enumerate(zip(SEED_EXAMPLES, vectors)):
        upsert_label_example(
            point_id=seed_point_id(i),
            vector=vector,
            payload={"label": label, "text": text},
        )
    print(f"Seeded {len(SEED_EXAMPLES)} label examples.")


if __name__ == "__main__":
    run()
