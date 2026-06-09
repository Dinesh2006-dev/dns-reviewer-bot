"""
PR Fetcher — Retrieves PR diff and file contents via GitHub API (PyGithub).
"""

from github import Github


def fetch_pr_diff(token: str, repo_name: str, pr_number: int) -> list[dict]:
    """
    Fetch changed files in a PR along with before/after content.
    Returns list of dicts with filename, patch, before, after.
    """
    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    files = []
    for f in pr.get_files():
        entry = {
            "filename": f.filename,
            "status": f.status,       # added, removed, modified
            "patch": f.patch or "",
            "before": "",
            "after": "",
        }

        # Fetch before content (from base branch)
        if f.status in ("modified", "removed"):
            try:
                base_content = repo.get_contents(f.filename, ref=pr.base.sha)
                entry["before"] = base_content.decoded_content.decode("utf-8")
            except Exception:
                entry["before"] = ""

        # Fetch after content (from PR head branch)
        if f.status in ("modified", "added"):
            try:
                head_content = repo.get_contents(f.filename, ref=pr.head.sha)
                entry["after"] = head_content.decoded_content.decode("utf-8")
            except Exception:
                entry["after"] = ""

        files.append(entry)

    return files
