import os

VECTORAI_HOST = os.environ.get("VECTORAI_HOST", "http://localhost:8080")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

TABS_COLLECTION = "tabs"
LABELS_COLLECTION = "labels"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

CLASSIFY_TOP_K = 5
NUDGE_CANDIDATE_LIMIT = 20
NUDGE_CARD_COUNT = 2

# Reference text embedded once at startup and used as the "actionable task"
# anchor for the semantic-closeness ranking side of the hybrid fusion.
ACTIONABLE_TASK_ANCHOR = "a task I need to finish or make progress on today"

DISTRACTION_DOMAINS = [
    "reddit.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
]

PORT = int(os.environ.get("PORT", "5000"))
