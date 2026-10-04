from github import GithubException


def create_pull_request(repo, branch, base):
    """Stage 2, part 1: open the Pull Request."""
    try:
        return repo.create_pull(
            title="AI Code Review Request",
            body="This Pull Request was automatically created for AI-powered code analysis.",
            head=branch, base=base)
    except GithubException:
        raise RuntimeError("Unable to create Pull Request.")


def read_pull_request(pr):
    """Stage 2, part 2: collect the PR details and the diff (the lines added and removed)."""
    files, parts = [], []
    for f in pr.get_files():
        files.append({"filename": f.filename, "additions": f.additions, "deletions": f.deletions})
        if f.patch:
            parts.append(f"--- file: {f.filename}\n{f.patch}")
    return {"pr_number": pr.number, "pr_url": pr.html_url, "files_changed": files,
            "additions": pr.additions, "deletions": pr.deletions, "diff": "\n\n".join(parts)}