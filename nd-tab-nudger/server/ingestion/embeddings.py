from openai import OpenAI

from config import OPENAI_API_KEY, EMBEDDING_MODEL

_client = None

# OpenAI rejects an empty input string. Tabs legitimately have blank titles
# while loading, so substitute a placeholder rather than 500 the request.
_EMPTY_PLACEHOLDER = "untitled page"


def get_openai_client():
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set — copy .env.example to .env and fill it in."
            )
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _clean(text):
    return (text or "").strip() or _EMPTY_PLACEHOLDER


def embed_text(text):
    return embed_texts([text])[0]


def embed_texts(texts):
    """Embed a list of strings in one API call.

    Returns vectors in the same order as `texts`. The API is documented to
    return results in order, but each item carries an explicit `index`, so
    sort by it rather than trusting order.
    """
    if not texts:
        return []

    client = get_openai_client()
    res = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[_clean(t) for t in texts],
    )
    return [item.embedding for item in sorted(res.data, key=lambda d: d.index)]
