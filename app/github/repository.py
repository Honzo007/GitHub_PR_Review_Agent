import re
import time

from github import GithubException

from app.github.client import get_client
from app.github.demo_files import DEMO_FILES

_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def parse_repo_url(url):
    """Accepts only links like https://github.com/user/repo and returns 'user/repo'."""
    match = _URL.match(url.strip())
    if not match:
        raise ValueError("Please enter a link like https://github.com/user/repository")
    return f"{match.group(1)}/{match.group(2)}"


_PR_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/(\d+)(?:[/?#].*)?$")


def parse_pr_url(url):
    """Accepts links like https://github.com/owner/repo/pull/12 and returns ('owner/repo', 12)."""
    match = _PR_URL.match(url.strip())
    if not match:
        raise ValueError("Please enter a link like https://github.com/owner/repo/pull/12")
    return f"{match.group(1)}/{match.group(2)}", int(match.group(3))


def open_repository(repo_url):
    """Stage 1, part 1: connect to GitHub and open the repository."""
    full_name = parse_repo_url(repo_url)
    try:
        return get_client().get_repo(full_name)
    except GithubException as e:
        if e.status == 401:
            raise PermissionError("GitHub authentication failed. Check your GitHub token.")
        raise LookupError("Unable to access this GitHub repository. Check the URL and GitHub permissions.")


def create_review_branch(repo):
    """Stage 1, part 2: make a new branch from the default branch (a timestamp keeps the name unique)."""
    base = repo.default_branch
    sha = repo.get_branch(base).commit.sha
    name = "ai-review/test-changes-" + time.strftime("%Y%m%d-%H%M%S")
    repo.create_git_ref(ref="refs/heads/" + name, sha=sha)
    return name, base


def push_demo_files(repo, branch):
    """Stage 1, part 3: commit the demo files to the new branch. Each file is one commit and one push."""
    folder = "review_demo/" + branch.split("test-changes-")[-1]   # new folder each run, so there is always a diff
    for filename, content in DEMO_FILES.items():
        repo.create_file(f"{folder}/{filename}", f"Add demo file {filename}", content, branch=branch)
    return folder
