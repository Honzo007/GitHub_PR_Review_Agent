import re

_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def parse_repo_url(url):
    """Accepts only links like https://github.com/user/repo and returns 'user/repo'."""
    match = _URL.match(url.strip())
    if not match:
        raise ValueError("Please enter a link like https://github.com/user/repository")
    return f"{match.group(1)}/{match.group(2)}"