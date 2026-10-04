import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.github.pull_request import create_pull_request, read_pull_request
from app.github.repository import create_review_branch, open_repository, push_demo_files

url = input("Test repo URL: ").strip()
repo = open_repository(url)
print("Connected to", repo.full_name)
branch, base = create_review_branch(repo)
print("Branch created:", branch)
folder = push_demo_files(repo, branch)
print("Demo files pushed to", folder)
pr = create_pull_request(repo, branch, base)
info = read_pull_request(pr)
print("Pull Request:", info["pr_url"])
print("Files:", [f["filename"] for f in info["files_changed"]])
print("Diff preview:")
print(info["diff"][:500])
