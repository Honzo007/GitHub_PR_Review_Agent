import threading

from flask import Blueprint, Response, jsonify, request

from app.github.repository import parse_pr_url, parse_repo_url
from app.services.event_manager import create_review, get_review
from app.services.reviewer import run_review
from app.sse import stream_events

bp = Blueprint("api", __name__)


@bp.post("/api/review")
def start_review():
    """Body: {"pr_url": "https://github.com/o/r/pull/1"}  (review a real PR)
       or   {"repo_url": "https://github.com/o/r"}        (demo mode)"""
    data = request.get_json(silent=True) or {}
    pr_url = str(data.get("pr_url", "")).strip()
    repo_url = str(data.get("repo_url", "")).strip()
    try:
        if pr_url:
            parse_pr_url(pr_url)
        else:
            parse_repo_url(repo_url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    review_id = create_review()
    threading.Thread(target=run_review, args=(review_id, repo_url, pr_url), daemon=True).start()
    return jsonify({"review_id": review_id, "status": "started"})


@bp.get("/api/review/<review_id>/events")
def events(review_id):
    return Response(stream_events(review_id), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@bp.get("/api/review/<review_id>")
def get_result(review_id):
    review = get_review(review_id)
    if review is None:
        return jsonify({"error": "Review not found"}), 404
    if review["result"] is None:
        return jsonify({"status": review["status"]})
    return jsonify({"status": review["status"], **review["result"]})