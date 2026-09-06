"""
Seeds the `labels` collection with hand-written example titles so
classification has something to compare against. Run once after the DB
is up:

    python -m ingestion.seed_labels
"""

from ingestion.embeddings import embed_text
from vectordb.client import ensure_collections, upsert_label_example

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
    for i, (label, text) in enumerate(SEED_EXAMPLES):
        vector = embed_text(text)
        upsert_label_example(
            point_id=f"seed-{i}",
            vector=vector,
            payload={"label": label, "text": text},
        )
    print(f"Seeded {len(SEED_EXAMPLES)} label examples.")


if __name__ == "__main__":
    run()
