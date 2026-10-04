import os

from dotenv import load_dotenv
from github import Auth, Github


def get_client():
    """Logs in to GitHub using the token from the .env file."""
    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise PermissionError("GitHub authentication failed. Check your GitHub token.")
    return Github(auth=Auth.Token(token))
