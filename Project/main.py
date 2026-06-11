"""
IM-08 DNS Zone File Reviewer — Main Orchestrator
Entry point for the agent pipeline.
"""

import os
import time
from dotenv import load_dotenv
from pr_fetcher import fetch_pr_diff
from diff_parser import parse_diff
from dns_validator import validate_zone
from rule_engine import check_rules
from llm_analyzer import analyze_with_llm, analyze_batch_with_llm
from formatter import format_review
from pr_commenter import post_comment

load_dotenv()

def get_origin_from_filename(filename: str) -> str:
    """Extract origin domain from file name (e.g. Project/zones/example.com.txt -> example.com.)"""
    basename = os.path.basename(filename)
    for ext in (".txt", ".zone", ".db"):
        if basename.endswith(ext):
            basename = basename[:-len(ext)]
            break
    if not basename.endswith("."):
        basename += "."
    return basename


def run_agent():
    token    = os.environ["GITHUB_TOKEN"]
    repo     = os.environ["GITHUB_REPO"]
    pr_num   = int(os.environ["PR_NUMBER"])

    print(f"[Agent] Starting DNS review for PR #{pr_num} in {repo}")

    # Step 1: Fetch PR diff
    changed_files = fetch_pr_diff(token, repo, pr_num)
    zone_files = [f for f in changed_files if f["filename"].startswith("Project/zones/")]

    if not zone_files:
        print("[Agent] No zone files changed. Skipping.")
        return

    all_results = []

    for zone_file in zone_files:
        print(f"[Agent] Reviewing: {zone_file['filename']}")
        
        origin = get_origin_from_filename(zone_file["filename"])

        # Step 2: Parse diff
        changes = parse_diff(zone_file["patch"], zone_file.get("before", ""), zone_file.get("after", ""))

        # Step 3: Validate DNS syntax
        syntax_errors = validate_zone(zone_file.get("after", ""), origin=origin)

        # Step 4: Apply risk rules
        rule_flags = check_rules(changes)

        # Step 5: LLM analysis
        llm_results = analyze_batch_with_llm(changes)

        all_results.append({
            "filename": zone_file["filename"],
            "changes": changes,
            "syntax_errors": syntax_errors,
            "rule_flags": rule_flags,
            "llm_results": llm_results,
        })

    # Step 6: Format review comment
    comment = format_review(all_results)

    # Step 7: Post to GitHub PR
    post_comment(token, repo, pr_num, comment)
    print("[Agent] Review posted to PR successfully!")

if __name__ == "__main__":
    run_agent()
