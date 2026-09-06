import json
import logging

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, HIGH_PRESSURE_VISIT_THRESHOLD
from nudging.session_state import get_distraction_pressure

log = logging.getLogger(__name__)

_client = None

# gemini-flash-latest returned 503 UNAVAILABLE ("high demand") on roughly two
# of every three calls during testing, and gemini-2.5-flash 404s on this key.
# flash-lite-latest was 3/3 and is plenty for one short line per tab.
MODEL = "gemini-flash-lite-latest"

FALLBACK_OVERLAY_LINE = "Something's waiting for you back in your tabs."

# Must be a types.Schema, not a plain dict. As a dict the schema was silently
# not enforced: the model answered with a markdown preamble instead of JSON
# and hit MAX_TOKENS before emitting any, so every call fell back.
RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "card_lines": types.Schema(
            type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)
        ),
        "overlay_line": types.Schema(type=types.Type.STRING),
    },
    required=["card_lines", "overlay_line"],
)

# Grounded in ADHD task-initiation research, not just "be nice":
#   - Implementation intentions (Gollwitzer): a concrete if-you-open-this,
#     do-this-next beats a vague reminder to "get back to it."
#   - Next-smallest-step framing: naming one tiny, doable action lowers the
#     activation-energy barrier further than naming the whole task does.
#   - Importance alone doesn't reliably trigger initiation for ADHD attention
#     — novelty/curiosity does more work than urgency, so lines should open
#     a small curiosity gap about the tab rather than lecture on priority.
#   - Zeigarnik effect: unfinished things already nag at attention on their
#     own — the copy can lean on that ("this is still open in your head")
#     instead of manufacturing urgency or guilt.
#   - Never shame: no "you should", "you need to", no guilt-based language.
SYSTEM_PROMPT = """You write short, playful nudge copy for a neurodivergent-friendly
tab-management tool, for an ADHD-primary audience. Tone: witty, warm, a clever
friend noticing something — never a productivity app scolding you. One short
sentence per line, under 90 characters. Never use guilt-based language
("you should", "you need to", "you've been ignoring").

Ground every line in how ADHD attention actually restarts a task, not generic
encouragement:
- Name ONE tiny, concrete next action inferred from the title/domain (e.g.
  "skim the first paragraph", "leave one comment") — never the whole task.
  This is an implementation-intention / next-smallest-step move: a specific
  doable action beats a vague reminder.
- Reach for curiosity or mild novelty over importance or urgency — "importance"
  alone doesn't reliably restart an ADHD brain, curiosity does more work.
  A small curiosity gap ("wonder what page 2 says") beats "this matters."
- It's fine to lean on the fact that unfinished things already nag at
  attention on their own (the tab's just sitting there, half-done) — that's
  real and can be named lightly, without turning it into guilt.

You'll also get a "pressure" field: "high" means the person has bounced
between distraction sites several times recently, so be extra concrete and
low-effort in the single line you write — the smallest possible next action,
not a bigger ask. "normal" means no adjustment needed.

Given a list of tabs (title + domain + label) and the pressure level, return
- "card_lines": one line per input tab, same order, each naming one tiny next
  action for that tab
- "overlay_line": one line about the single most actionable tab, meant to
  gently interrupt someone who just landed on a distraction site — should
  name that tab specifically, not speak in the abstract
"""


def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _pressure_level():
    visit_count, _ = get_distraction_pressure()
    return "high" if visit_count >= HIGH_PRESSURE_VISIT_THRESHOLD else "normal"


def generate_copy(candidate_tabs):
    """candidate_tabs: list of {title, domain, label} dicts (already ranked)."""
    if not candidate_tabs:
        return [], "Nothing waiting on you right now — just vibes."

    fallback_lines = ["Still here, whenever you’re ready." for _ in candidate_tabs]

    payload = {
        "pressure": _pressure_level(),
        "tabs": [
            {"title": t["title"], "domain": t["domain"], "label": t.get("label")}
            for t in candidate_tabs
        ],
    }

    try:
        client = get_client()
        response = client.models.generate_content(
            model=MODEL,
            contents=json.dumps(payload),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                # 400 was not enough headroom: a short preamble consumed the
                # budget and the response finished on MAX_TOKENS mid-JSON.
                max_output_tokens=800,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
    except Exception:
        # Gemini 503s intermittently. Degrade to the static lines rather than
        # letting the exception escape and take /nudge down with it.
        log.warning("copy generation failed, using fallback lines", exc_info=True)
        return fallback_lines, FALLBACK_OVERLAY_LINE

    try:
        parsed = json.loads(response.text)
        card_lines = parsed["card_lines"]
        overlay_line = parsed["overlay_line"]
        if len(card_lines) != len(candidate_tabs):
            raise ValueError("card_lines length mismatch")
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        card_lines = ["Still here, whenever you're ready." for _ in candidate_tabs]
        overlay_line = FALLBACK_OVERLAY_LINE

    return card_lines, overlay_line
