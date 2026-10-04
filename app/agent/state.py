from typing import TypedDict


class ReviewState(TypedDict, total=False):
    """The shared notebook. Every review step reads from it and writes to it."""
    repo_url: str
    repository: str
    pr_number: int
    branch_name: str
    files_changed: list
    diff: str
    bugs: list
    security_issues: list
    quality_issues: list
    all_findings: list      # merged, de-duplicated, sorted findings
    counts: dict            # how many findings per severity
    review_summary: str
    final_verdict: str
    status: str
    errors: list