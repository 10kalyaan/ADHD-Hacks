import os

from dotenv import load_dotenv

# Reads ../.env (next to docker-compose.yml). Without this the API keys in
# the team's .env are simply never seen.
load_dotenv(os.path.join(os.path.dirname(__file__), os.pardir, ".env"))

# gRPC endpoint: bare host:port, no scheme. 6574 is the SDK's default gRPC
# port (6573 is REST) — see docker-compose.yml. vectordb/client.py imports
# this name, so keep it VECTORAI_URL rather than VECTORAI_HOST.
VECTORAI_URL = os.environ.get("VECTORAI_URL", "localhost:6574")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# The three buckets every tab lands in. Deliberately non-judgemental names --
# "chill" rather than "distraction" -- since the whole point is to nudge
# without shaming. These strings are the contract: they are stored in the DB
# payload, returned by /ingest and /nudge, and styled by the extension.
LABEL_WORK = "work"
LABEL_SIDEQUEST = "sidequest"
LABEL_CHILL = "chill"
LABELS = (LABEL_WORK, LABEL_SIDEQUEST, LABEL_CHILL)

TABS_COLLECTION = "tabs"
LABELS_COLLECTION = "labels"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

CLASSIFY_TOP_K = 5
# How many tabs the ranker will consider for cards. This is NOT how many tabs
# get read from the DB -- that is MAX_TRACKED_TABS. Conflating the two capped
# the New Tab page's "tabs open" count at 20.
NUDGE_CANDIDATE_LIMIT = 20
NUDGE_CARD_COUNT = 2

# Upper bound when reconciling stored tabs against the browser's open set
# (/tabs/sync). Generous enough to cover even a heavy tab-hoarding session.
MAX_TRACKED_TABS = 500

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
