import json

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY

_client = None

SYSTEM_PROMPT = """You write short, playful nudge copy for a neurodivergent-friendly
tab-management tool. Tone: witty, warm, never shaming or judgmental — think a
clever friend, not a productivity app scolding you. One short sentence per line,
under 90 characters. Never use guilt-based language ("you should", "you need to").

Given a list of tabs (title + domain + label), return JSON with:
- "card_lines": one line per input tab, same order, each nudging the user toward
  that tab without being preachy
- "overlay_line": one line referencing the single most actionable tab, meant to
  gently interrupt someone who just landed on a distraction site

Return ONLY valid JSON, no prose, shape:
{"card_lines": ["...", "..."], "overlay_line": "..."}
"""


def get_client():
    global _client
    if _client is None:
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def generate_copy(candidate_tabs):
    """candidate_tabs: list of {title, domain, label} dicts (already ranked)."""
    if not candidate_tabs:
        return [], "Nothing waiting on you right now — just vibes."

    client = get_client()
    user_content = json.dumps(
        [{"title": t["title"], "domain": t["domain"], "label": t.get("label")} for t in candidate_tabs]
    )

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text
    parsed = json.loads(raw)
    return parsed["card_lines"], parsed["overlay_line"]
