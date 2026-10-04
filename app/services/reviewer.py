import time

from app.services.event_manager import emit, set_result

# FAKE steps for now. Later these become the real GitHub and AI steps.
FAKE_STEPS = [
    ("github", "running", "Connecting to GitHub..."),
    ("github", "completed", "Repository validated, branch created, code pushed"),
    ("pr", "running", "Creating Pull Request..."),
    ("pr", "completed", "Pull Request created"),
    ("bug_analysis", "running", "Starting bug analysis..."),
    ("bug_analysis", "completed", "Bug analysis finished"),
    ("security_analysis", "running", "Starting security analysis..."),
    ("security_analysis", "completed", "Security analysis finished"),
    ("quality_analysis", "running", "Starting code quality analysis..."),
    ("quality_analysis", "completed", "Code quality analysis finished"),
    ("final_verdict", "running", "Generating final verdict..."),
    ("final_verdict", "completed", "Review completed"),
]

FAKE_RESULT = {
    "verdict": "CHANGES_REQUESTED",
    "summary": "The pull request contains security and correctness issues that should be fixed before merging.",
    "total_issues": 2, "critical": 0, "high": 1, "medium": 1, "low": 0,
    "issues": [
        {"file": "login.py", "line": 12, "severity": "high", "title": "Hardcoded password",
         "explanation": "A password is written in the source code.", "fix": "Use an environment variable."},
        {"file": "utils.py", "line": 30, "severity": "medium", "title": "Missing None check",
         "explanation": "The value can be None and crash the program.", "fix": "Check for None first."},
    ],
}


def run_review(review_id, repo_url):
    try:
        for stage, status, message in FAKE_STEPS:
            emit(review_id, stage, status, message)
            time.sleep(1)
        set_result(review_id, FAKE_RESULT)
    except Exception:
        emit(review_id, "error", "failed", "Something went wrong. Please try again.")
        set_result(review_id, None, "failed")
    finally:
        emit(review_id, "done", "completed", "")