import queue
import threading
import uuid

_reviews = {}
_lock = threading.Lock()


def create_review():
    """Makes a new review with its own ID and its own list of progress messages."""
    review_id = uuid.uuid4().hex[:8]
    with _lock:
        _reviews[review_id] = {"events": queue.Queue(), "result": None, "status": "started"}
    return review_id


def emit(review_id, stage, status, message=""):
    """Adds one progress message, for example: bug_analysis, running, 'Starting bug analysis...'."""
    review = _reviews.get(review_id)
    if review:
        review["events"].put({"stage": stage, "status": status, "message": message})


def set_result(review_id, result, status="completed"):
    review = _reviews.get(review_id)
    if review:
        review["result"] = result
        review["status"] = status


def get_review(review_id):
    return _reviews.get(review_id)