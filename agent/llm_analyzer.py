"""
LLM Analyzer — Uses OpenRouter API (Llama 3.1 8B Free) or local Ollama (Mistral) to classify DNS change risk.
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL      = os.environ.get("OLLAMA_MODEL", "mistral")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")

SYSTEM_PROMPT = """You are a DNS security expert reviewing DNS zone file changes.
Analyze each DNS record change and classify its risk level.
Always respond in valid JSON only. No explanation outside JSON."""

def analyze_with_llm(change: dict) -> dict:
    """
    Send a DNS change to OpenRouter (if API key is present) or Ollama LLM for risk classification.
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

    use_openrouter = bool(OPENROUTER_API_KEY)

    try:
        if use_openrouter:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/Dinesh2006-dev/dns-reviewer-bot",
                "X-Title": "DNS Reviewer Bot",
                "Content-Type": "application/json",
            }
            payload = {
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            }
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            raw_text = response.json()["choices"][0]["message"]["content"]
        else:
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

    except Exception as e:
        # Fallback if LLM unavailable
        provider = "OpenRouter" if use_openrouter else "Ollama"
        return {
            "change": change["raw"],
            "risk_level": "warning",
            "explanation": f"LLM analysis via {provider} unavailable ({e}). Manual review recommended.",
            "suggestion": "Review this change manually before merging.",
        }

