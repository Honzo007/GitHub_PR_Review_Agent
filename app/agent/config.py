# All review rules live here, so they can be changed in ONE place.

SEVERITY_ORDER = ["critical", "high", "medium", "low"]

# Checked from top to bottom. The first severity that has at least one finding decides the verdict.
VERDICT_RULES = [
    ("critical", "CHANGES_REQUESTED"),
    ("high", "CHANGES_REQUESTED"),
    ("medium", "REVIEW_REQUIRED"),
    ("low", "APPROVE"),
]
DEFAULT_VERDICT = "APPROVE"   # used when there are no findings at all

ALLOWED_VERDICTS = {"APPROVE", "CHANGES_REQUESTED", "REVIEW_REQUIRED"}

MODEL = "gemini-2.5-flash"    # if it stops working, check Google AI Studio for the current free model
MAX_DIFF_CHARS = 60000        # very large diffs are cut to this size
