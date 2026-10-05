from github import GithubException

MAX_FILES = 60   # a very large PR is cut to this many files


def create_pull_request(repo, branch, base):
    """Demo mode: open the Pull Request."""
    try:
        return repo.create_pull(
            title="AI Code Review Request",
            body="This Pull Request was automatically created for AI-powered code analysis.",
            head=branch, base=base)
    except GithubException:
        raise RuntimeError("Unable to create Pull Request.")


def get_pull_request(repo, number):
    """Real mode: load a Pull Request that a person already opened."""
    try:
        return repo.get_pull(number)
    except GithubException as e:
        if e.status == 404:
            raise LookupError("Pull Request not found. Check the link and the GitHub permissions.")
        raise


def read_pull_request(pr):
    """Collects the PR details and the diff (the lines added and removed)."""
    files, parts = [], []
    for f in pr.get_files():
        if len(files) >= MAX_FILES:
            break
        files.append({"filename": f.filename, "additions": f.additions, "deletions": f.deletions})
        if f.patch:                                  # binary files have no patch
            parts.append(f"--- file: {f.filename}\n{f.patch}")
    return {"pr_number": pr.number, "pr_url": pr.html_url, "pr_title": (pr.title or "")[:120],
            "files_changed": files, "files_total": pr.changed_files,
            "additions": pr.additions, "deletions": pr.deletions, "diff": "\n\n".join(parts)}