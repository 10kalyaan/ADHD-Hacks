import logging
import time

from flask import Blueprint, request, jsonify

from ingestion.embeddings import embed_text
from ingestion.classifier import classify_title
from nudging.session_state import record_distraction_visit
from vectordb.client import upsert_tab

log = logging.getLogger(__name__)

ingestion_bp = Blueprint("ingestion", __name__)


@ingestion_bp.route("/ingest", methods=["POST"])
def ingest():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"status": "error", "error": "expected a JSON object body"}), 400

    # tabId is the point id, so it's the one field we can't default. The DB
    # only accepts a non-negative int or a UUID as an id — Chrome tab ids are
    # non-negative ints, so they go in as-is (str(tab_id) is rejected).
    if body.get("tabId") is None:
        return jsonify({"status": "error", "error": "tabId is required"}), 400
    try:
        tab_id = int(body["tabId"])
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": "tabId must be an integer"}), 400
    if tab_id < 0:
        return jsonify({"status": "error", "error": "tabId must be non-negative"}), 400

    title = body.get("title") or ""
    url = body.get("url") or ""
    domain = body.get("domain") or ""
    opened_at = body.get("openedAt") or int(time.time() * 1000)

    try:
        vector = embed_text(title)
        label = classify_title(vector)

        if label == "distraction":
            record_distraction_visit(domain)

        upsert_tab(
            point_id=tab_id,
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
    except Exception:
        # background.js fires these constantly; a JSON error keeps the
        # extension side debuggable instead of handing it an HTML traceback.
        log.exception("ingest failed for tabId=%s", tab_id)
        return jsonify({"status": "error", "error": "ingest failed"}), 502

    return jsonify({"status": "ok", "label": label})
