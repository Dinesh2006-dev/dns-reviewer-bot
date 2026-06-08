"""
Formatter — Builds the final markdown review comment for the GitHub PR.
"""

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high":     "🟠",
    "high_risk":"🟠",
    "warning":  "⚠️",
    "safe":     "✅",
}


def format_review(all_results: list[dict]) -> str:
    lines = ["## 🤖 DNS Zone Review Bot\n"]
    lines.append("*Automated review powered by Mistral 7B + dnspython*\n")
    lines.append("---\n")

    total_changes = sum(len(r["changes"]) for r in all_results)
    total_flags   = sum(len(r["rule_flags"]) for r in all_results)
    critical_count = sum(
        1 for r in all_results
        for f in r["rule_flags"] if f["severity"] == "critical"
    )

    lines.append(f"**📋 Summary:** {total_changes} change(s) detected")
    if critical_count:
        lines.append(f" | 🔴 {critical_count} critical")
    if total_flags - critical_count > 0:
        lines.append(f" | ⚠️ {total_flags - critical_count} warning(s)")
    lines.append("\n\n---\n")

    for result in all_results:
        lines.append(f"### 📄 File: `{result['filename']}`\n")

        # Syntax errors
        if result["syntax_errors"]:
            lines.append("#### 🚫 Syntax Errors\n")
            for err in result["syntax_errors"]:
                lines.append(f"- **Line {err['line']}:** {err['error']}\n")
            lines.append("\n")

        # Rule flags
        if result["rule_flags"]:
            lines.append("#### 📏 Rule-Based Checks\n")
            for flag in result["rule_flags"]:
                emoji = SEVERITY_EMOJI.get(flag["severity"], "⚠️")
                lines.append(f"{emoji} **{flag['severity'].upper()} — {flag['rule'].replace('_', ' ').title()}**\n")
                lines.append(f"- Record: `{flag['change']}`\n")
                lines.append(f"- Issue: {flag['message']}\n")
                lines.append(f"- Suggestion: _{flag['suggestion']}_\n\n")

        # LLM results
        if result["llm_results"]:
            lines.append("#### 🧠 AI Risk Analysis (Mistral 7B)\n")
            for llm in result["llm_results"]:
                emoji = SEVERITY_EMOJI.get(llm.get("risk_level", "warning"), "⚠️")
                lines.append(f"{emoji} **{llm.get('risk_level', 'unknown').upper().replace('_', ' ')}**\n")
                lines.append(f"- Record: `{llm.get('change', '')}`\n")
                lines.append(f"- Analysis: {llm.get('explanation', '')}\n")
                if llm.get("suggestion"):
                    lines.append(f"- Suggestion: _{llm.get('suggestion')}_\n")
                lines.append("\n")

        lines.append("---\n")

    lines.append("\n*⚡ Review completed automatically | IM-08 DNS Zone Reviewer*")
    return "".join(lines)
