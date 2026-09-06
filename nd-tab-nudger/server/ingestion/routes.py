from flask import Blueprint, request, jsonify

from ingestion.embeddings import embed_text
from ingestion.classifier import classify_title
from vectordb.client import upsert_tab

ingestion_bp = Blueprint("ingestion", __name__)


@ingestion_bp.route("/ingest", methods=["POST"])
def ingest():
    body = request.get_json(force=True)

    tab_id = body["tabId"]
    title = body["title"]
    url = body["url"]
    domain = body["domain"]
    opened_at = body["openedAt"]

    vector = embed_text(title)
    label = classify_title(vector)

    upsert_tab(
        point_id=str(tab_id),
        vector=vector,
        payload={
            "tabId": tab_id,
            "title": title,
            "url": url,
            "domain": domain,
            "openedAt": opened_at,
            "label": label,
        },
    )

    return jsonify({"status": "ok", "label": label})
