from openai import OpenAI

from config import OPENAI_API_KEY, EMBEDDING_MODEL

_client = None


def get_openai_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def embed_text(text):
    client = get_openai_client()
    res = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return res.data[0].embedding
