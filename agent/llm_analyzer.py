"""
LLM Analyzer — Uses Ollama (Mistral 7B) to classify DNS change risk.
"""

import requests
import json


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "mistral"

SYSTEM_PROMPT = """You are a DNS security expert reviewing DNS zone file changes.
Analyze each DNS record change and classify its risk level.
Always respond in valid JSON only. No explanation outside JSON."""

def analyze_with_llm(change: dict) -> dict:
    """
    Send a DNS change to Ollama LLM for risk classification.
    Returns dict with risk_level, explanation, suggestion.
    """
    record = change.get("record", {})
    prompt = f"""Analyze this DNS record change:

Change type: {change['type']}
Raw record: {change['raw']}
Record name: {record.get('name', 'unknown')}
Record type: {record.get('rtype', 'unknown')}
TTL: {record.get('ttl', 'not set')}
Value: {record.get('value', 'unknown')}

Respond ONLY with this JSON structure:
{{
  "risk_level": "safe|warning|high_risk|critical",
  "explanation": "2 sentence explanation of why this risk level",
  "suggestion": "one actionable suggestion or null if safe"
}}"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "system": SYSTEM_PROMPT, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        raw_text = response.json().get("response", "{}")

        # Strip markdown code fences if present
        raw_text = raw_text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        result = json.loads(raw_text.strip())
        result["change"] = change["raw"]
        return result

    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        # Fallback if LLM unavailable
        return {
            "change": change["raw"],
            "risk_level": "warning",
            "explanation": f"LLM analysis unavailable ({e}). Manual review recommended.",
            "suggestion": "Review this change manually before merging.",
        }
