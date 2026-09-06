import os

from dotenv import load_dotenv

# Reads ../.env (next to docker-compose.yml). Without this the API keys in
# the team's .env are simply never seen.
load_dotenv(os.path.join(os.path.dirname(__file__), os.pardir, ".env"))

# gRPC endpoint: bare host:port, no scheme. 6574 is the SDK's default gRPC
# port (6573 is REST) — see docker-compose.yml.
VECTORAI_URL = os.environ.get("VECTORAI_URL", "localhost:6574")
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
