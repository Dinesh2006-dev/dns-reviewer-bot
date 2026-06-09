"""
PR Commenter — Posts the review comment to GitHub PR via PyGithub.
"""

import os
from github import Github


def post_comment(token: str, repo_name: str, pr_number: int, comment: str):
    """Post review comment to a GitHub PR."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    pr.create_issue_comment(comment)
    print(f"[Commenter] Posted review comment to PR #{pr_number}")

    # Add risk label
    _add_labels(repo, pr, comment)

    # Optional Discord notification
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook:
        _notify_discord(webhook, repo_name, pr_number, comment)


def _add_labels(repo, pr, comment: str):
    """Add dns-reviewed label and risk level label to PR."""
    try:
        existing = [l.name for l in repo.get_labels()]

        for label_name, color in [
            ("dns-reviewed", "0075ca"),
            ("risk:critical", "d93f0b"),
            ("risk:warning", "e4e669"),
        ]:
            if label_name not in existing:
                repo.create_label(label_name, color)

        labels = ["dns-reviewed"]
        if "🔴 CRITICAL" in comment or "CRITICAL" in comment:
            labels.append("risk:critical")
        elif "⚠️" in comment:
            labels.append("risk:warning")

        pr.add_to_labels(*labels)
    except Exception as e:
        print(f"[Commenter] Label error (non-critical): {e}")


def _notify_discord(webhook_url: str, repo: str, pr_number: int, comment: str):
    """Send a brief alert to Discord channel."""
    import requests
    has_critical = "CRITICAL" in comment
    emoji = "🚨" if has_critical else "⚠️"
    message = {
        "content": (
            f"{emoji} **DNS Review Alert** | `{repo}` PR #{pr_number}\n"
            f"{'🔴 CRITICAL risk detected! Review before merge.' if has_critical else '✅ Review complete. Check PR for details.'}\n"
            f"https://github.com/{repo}/pull/{pr_number}"
        )
    }
    try:
        requests.post(webhook_url, json=message, timeout=10)
        print("[Commenter] Discord notification sent.")
    except Exception as e:
        print(f"[Commenter] Discord error (non-critical): {e}")
