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


def calculate_risk_score(all_results: list[dict]) -> tuple[int, str]:
    has_syntax_errors = any(len(r["syntax_errors"]) > 0 for r in all_results)
    if has_syntax_errors:
        return 100, "🔴 CRITICAL (Syntax Outage Risk)"
    
    score = 0
    for r in all_results:
        for f in r["rule_flags"]:
            sev = f.get("severity", "warning").lower()
            if sev == "critical":
                score += 40
            elif sev == "high" or sev == "high_risk":
                score += 20
            elif sev == "warning":
                score += 10

    score = min(score, 100)
    
    if score >= 81:
        category = "🔴 CRITICAL RISK"
    elif score >= 51:
        category = "🟠 HIGH RISK"
    elif score >= 21:
        category = "⚠️ WARNING"
    else:
        category = "✅ SAFE"
        
    return score, category


def format_review(all_results: list[dict]) -> str:
    import llm_analyzer
    if llm_analyzer.OPENROUTER_API_KEY:
        model_name = f"OpenRouter ({llm_analyzer.OPENROUTER_MODEL})"
    else:
        model_name = f"Ollama ({llm_analyzer.MODEL})"

    lines = ["## 🤖 DNS Zone Review Bot\n"]
    lines.append(f"*Automated review powered by {model_name} + dnspython*\n")
    lines.append("---\n")

    total_changes = sum(len(r["changes"]) for r in all_results)
    total_flags   = sum(len(r["rule_flags"]) for r in all_results)
    critical_count = sum(
        1 for r in all_results
        for f in r["rule_flags"] if f["severity"] == "critical"
    )

    score, category = calculate_risk_score(all_results)

    lines.append(f"**📋 Summary:** {total_changes} change(s) detected")
    if critical_count:
        lines.append(f" | 🔴 {critical_count} critical")
    if total_flags - critical_count > 0:
        lines.append(f" | ⚠️ {total_flags - critical_count} warning(s)")
    lines.append(f"\n**🎯 Risk Score:** {score}/100 ({category})\n")
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
            lines.append(f"#### 🧠 AI Risk Analysis ({model_name})\n")
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
