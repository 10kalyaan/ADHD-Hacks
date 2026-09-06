import logging
import time

from flask import Blueprint, request, jsonify

from config import MAX_TRACKED_TABS, LABEL_CHILL
from ingestion.embeddings import embed_text
from ingestion.classifier import classify_title
from nudging.session_state import record_distraction_visit
from vectordb.client import upsert_tab, delete_tabs, scroll_all_tabs, get_tab

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


@ingestion_bp.route("/tabs/visit", methods=["POST"])
def visit_tab():
    """Record that the user actually switched to a tab.

    Chill pressure means "how much are they bouncing onto low-value tabs right
    now". Deriving it at ingest time measured the wrong thing entirely -- how
    many chill tabs happened to be open -- and the MV3 backfill re-ingesting
    every tab on each service-worker restart pinned it permanently high, so
    the nudge was stuck at a single card. Only a real activation counts.
    """
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or body.get("tabId") is None:
        return jsonify({"status": "error", "error": "tabId is required"}), 400

    try:
        tab_id = int(body["tabId"])
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": "tabId must be an integer"}), 400

    try:
        payload = get_tab(tab_id)
    except Exception:
        log.exception("visit lookup failed for tabId=%s", tab_id)
        return jsonify({"status": "error", "error": "visit failed"}), 502

    if not payload:
        return jsonify({"status": "ok", "counted": False})

    counted = payload.get("label") == LABEL_CHILL
    if counted:
        record_distraction_visit(payload.get("domain") or "")

    return jsonify({"status": "ok", "counted": counted})


@ingestion_bp.route("/tabs/sync", methods=["POST"])
def sync_tabs():
    """Prune tabs the browser no longer has open.

    Reconciles against the full open-tab list rather than deleting one id at
    a time, so it also cleans up rows orphaned by a browser restart — the
    service worker never sees onRemoved for those.
    """
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("openTabIds"), list):
        return jsonify({"status": "error", "error": "openTabIds (list) is required"}), 400

    try:
        open_ids = {int(t) for t in body["openTabIds"]}
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": "openTabIds must be integers"}), 400

    try:
        stored = scroll_all_tabs(limit=MAX_TRACKED_TABS)
        stale = [p.id for p in stored if p.id not in open_ids]
        removed = delete_tabs(stale)
    except Exception:
        log.exception("tab sync failed")
        return jsonify({"status": "error", "error": "sync failed"}), 502

    return jsonify({"status": "ok", "removed": removed})
