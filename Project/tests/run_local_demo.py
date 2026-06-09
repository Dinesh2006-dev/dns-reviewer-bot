import os
import sys

# Add agent folder to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from diff_parser import parse_diff
from dns_validator import validate_zone
from rule_engine import check_rules
from llm_analyzer import analyze_with_llm
from formatter import format_review

def run_local_demo():
    print("=== DNS Reviewer Agent Local Demo ===")
    
    # 1. Define a mock diff patch simulating changes in Project/zones/example.com.txt
    mock_patch = (
        "--- Project/zones/example.com.txt\n"
        "+++ Project/zones/example.com.txt\n"
        "@@ -18,4 +18,6 @@\n"
        " www       3600    IN    A      93.184.216.34\n"
        "+*          60     IN    A      1.2.3.4\n"
        "+@          3600   IN    MX     10 mail.example.com.\n"
    )
    
    # 2. Define the new zone content (after changes)
    mock_after_content = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.example.com.
www  IN    A      93.184.216.34
*    60    IN    A      1.2.3.4
@    IN    MX     10 mail.example.com.
"""

    filename = "Project/zones/example.com.txt"
    print(f"\n[1] Simulating changes in: {filename}")
    
    # Extract origin
    from main import get_origin_from_filename
    origin = get_origin_from_filename(filename)
    print(f"    Resolved origin: {origin}")

    # Parse diff
    print("\n[2] Parsing Diff...")
    changes = parse_diff(mock_patch, "", mock_after_content)
    print(f"    Detected {len(changes)} changes:")
    for c in changes:
        print(f"      - {c['type'].upper()}: {c['raw']}")

    # Configure stdout to use UTF-8
    sys.stdout.reconfigure(encoding='utf-8')

    # Validate syntax
    print("\n[3] Running DNS Syntax Validation...")
    syntax_errors = validate_zone(mock_after_content, origin=origin)
    if not syntax_errors:
        print("    [OK] DNS Syntax: Valid!")
    else:
        print("    [ERROR] DNS Syntax Errors found:", syntax_errors)

    # Check rules
    print("\n[4] Running Rule Engine...")
    rule_flags = check_rules(changes)
    print(f"    Flagged {len(rule_flags)} rule issues:")
    for flag in rule_flags:
        print(f"      - {flag['severity'].upper()}: {flag['message']}")

    # Analyze with LLM
    import llm_analyzer
    provider_name = "OpenRouter (Llama 3.1 8B Free)" if llm_analyzer.OPENROUTER_API_KEY else "local Ollama (Mistral)"
    print(f"\n[5] Running LLM Risk Analysis via {provider_name}...")
    if not llm_analyzer.OPENROUTER_API_KEY:
        print("    (Note: Set OPENROUTER_API_KEY in .env to use OpenRouter Cloud API. Currently falling back to Ollama.)")
    llm_results = []
    for change in changes:
        res = analyze_with_llm(change)
        llm_results.append(res)
        print(f"      - Record: {res.get('change')}")
        print(f"        Risk Level: {res.get('risk_level').upper()}")
        print(f"        Explanation: {res.get('explanation')}")
        print(f"        Suggestion: {res.get('suggestion')}")

    # Format review comment
    print("\n[6] Formatting Review Comment...")
    all_results = [{
        "filename": filename,
        "changes": changes,
        "syntax_errors": syntax_errors,
        "rule_flags": rule_flags,
        "llm_results": llm_results
    }]
    review_comment = format_review(all_results)
    
    print("\n=== Generated Review Comment (Markdown) ===\n")
    print(review_comment)

if __name__ == "__main__":
    run_local_demo()
