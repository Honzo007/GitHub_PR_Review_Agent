from github import GithubException

from app.agent.config import SEVERITY_ORDER
from app.agent.graph import graph
from app.github.pull_request import create_pull_request, read_pull_request
from app.github.repository import create_review_branch, open_repository, push_demo_files
from app.services.event_manager import emit, set_result

# Progress messages sent to the browser after each graph step finishes.
AFTER_NODE = {
    "analyze_diff": [("bug_analysis", "running", "Starting bug analysis...")],
    "bug_analysis": [("bug_analysis", "completed", "Bug analysis finished"),
                     ("security_analysis", "running", "Starting security analysis...")],
    "security_analysis": [("security_analysis", "completed", "Security analysis finished"),
                          ("quality_analysis", "running", "Starting code quality analysis...")],
    "quality_analysis": [("quality_analysis", "completed", "Code quality analysis finished"),
                         ("final_verdict", "running", "Aggregating findings...")],
    "decide_verdict": [("final_verdict", "completed", "Review completed.")],
}


def _friendly(e):
    """Turns an error into a short message that is safe to show. Never includes secrets."""
    if isinstance(e, GithubException):
        if e.status == 401:
            return "GitHub authentication failed. Check your GitHub token."
        if e.status in (403, 404):
            return ("GitHub refused the request. Check that the token has read and write access to "
                    "Contents and Pull requests on this repository.")
        return "Unable to complete the GitHub request."
    if isinstance(e, KeyError):
        return "Something went wrong. Please try again."
    if isinstance(e, (PermissionError, LookupError, ValueError, RuntimeError)):
        return str(e)
    return "Something went wrong. Please try again."


def run_review(review_id, repo_url):
    stage = "github"
    try:
        # ---------- Stage 1: push code ----------
        emit(review_id, "github", "running", "Connecting to GitHub...")
        repo = open_repository(repo_url)
        emit(review_id, "github", "running", "Repository validated: " + repo.full_name)
        emit(review_id, "github", "running", "Creating review branch...")
        branch, base = create_review_branch(repo)
        emit(review_id, "github", "running", "Pushing code...")
        push_demo_files(repo, branch)
        emit(review_id, "github", "completed", "Code pushed to " + branch)

        # ---------- Stage 2: open PR ----------
        stage = "pr"
        emit(review_id, "pr", "running", "Creating Pull Request...")
        pr = create_pull_request(repo, branch, base)
        emit(review_id, "pr", "running", "Fetching PR diff...")
        info = read_pull_request(pr)
        emit(review_id, "pr", "completed", "Pull Request created: " + info["pr_url"])

        # ---------- Stage 3: AI review (LangGraph) ----------
        stage = "ai_review"
        state = {"repo_url": repo_url, "repository": repo.full_name, "pr_number": info["pr_number"],
                 "branch_name": branch, "files_changed": info["files_changed"], "diff": info["diff"], "errors": []}
        for update in graph.stream(state, stream_mode="updates"):
            for node, output in update.items():
                if output:
                    state.update(output)
                for event in AFTER_NODE.get(node, []):
                    emit(review_id, *event)

        counts, findings = state.get("counts", {}), state.get("all_findings", [])
        result = {
            "verdict": state.get("final_verdict", "REVIEW_REQUIRED"),
            "summary": state.get("review_summary", ""),
            "total_issues": len(findings),
            **{s: counts.get(s, 0) for s in SEVERITY_ORDER},
            "issues": findings,
            "warnings": state.get("errors", []),
            "repository": repo.full_name, "branch": branch,
            "pr_url": info["pr_url"], "pr_number": info["pr_number"],
            "files_analyzed": len(info["files_changed"]),
            "additions": info["additions"], "deletions": info["deletions"],
        }
        set_result(review_id, result)
    except Exception as e:
        emit(review_id, stage, "failed", _friendly(e))
        set_result(review_id, None, "failed")
    finally:
        emit(review_id, "done", "completed", "")
