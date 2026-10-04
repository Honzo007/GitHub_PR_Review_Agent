import json
import queue

from app.services.event_manager import get_review


def stream_events(review_id):
    """Sends the progress messages to the browser one by one (Server-Sent Events)."""
    review = get_review(review_id)
    if review is None:
        yield 'data: {"stage": "error", "status": "failed", "message": "Unknown review"}\n\n'
        return
    while True:
        try:
            event = review["events"].get(timeout=15)
        except queue.Empty:
            yield ": keep-alive\n\n"      # keeps the connection open while waiting
            continue
        yield "data: " + json.dumps(event) + "\n\n"
        if event["stage"] == "done":
            break