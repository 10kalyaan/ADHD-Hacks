import os

VECTORAI_HOST = os.environ.get("VECTORAI_HOST", "localhost:6574")  # gRPC port
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

TABS_COLLECTION = "tabs"
LABELS_COLLECTION = "labels"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

CLASSIFY_TOP_K = 5
NUDGE_CANDIDATE_LIMIT = 20
NUDGE_CARD_COUNT = 2

# Distraction-domain visits within session_state's rolling window before a
# nudge switches to showing just one card instead of NUDGE_CARD_COUNT — see
# nudging/session_state.py and nudging/ranking.py::_card_count_for_pressure.
HIGH_PRESSURE_VISIT_THRESHOLD = 3

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
