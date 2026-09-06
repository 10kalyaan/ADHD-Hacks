from flask import Blueprint, jsonify

from nudging.ranking import rank_nudge_candidates
from nudging.copy_generator import generate_copy

nudging_bp = Blueprint("nudging", __name__)


@nudging_bp.route("/nudge", methods=["GET"])
def nudge():
    candidates, all_tabs = rank_nudge_candidates()
    lines, overlay_line = generate_copy(candidates)

    cards = [
        {
            "tabId": tab["tabId"],
            "title": tab["title"],
            "domain": tab["domain"],
            "line": line,
            "label": tab.get("label"),
        }
        for tab, line in zip(candidates, lines)
    ]

    card_ids = {c["tabId"] for c in cards}
    open_tabs = [
        {
            "tabId": t["tabId"],
            "title": t["title"],
            "domain": t["domain"],
            "openedAt": t["openedAt"],
        }
        for t in all_tabs
        if t["tabId"] not in card_ids
    ]

    return jsonify({"cards": cards, "overlay_line": overlay_line, "open_tabs": open_tabs})
