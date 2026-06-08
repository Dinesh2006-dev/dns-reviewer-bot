# 📝 Prompts Documentation — IM-08 DNS Zone File Reviewer
> Mandatory requirement: All AI prompts used during development and in the agent.

---

## 1. LLM Risk Classification Prompt (Used in Production)
**File:** `agent/llm_analyzer.py`

```
SYSTEM:
You are a DNS security expert reviewing DNS zone file changes.
Analyze each DNS record change and classify its risk level.
Always respond in valid JSON only. No explanation outside JSON.

USER:
Analyze this DNS record change:

Change type: {added|removed|modified}
Raw record: {raw DNS record line}
Record name: {record name}
Record type: {A|AAAA|CNAME|MX|NS|TXT|SOA}
TTL: {ttl value or "not set"}
Value: {record value}

Respond ONLY with this JSON structure:
{
  "risk_level": "safe|warning|high_risk|critical",
  "explanation": "2 sentence explanation of why this risk level",
  "suggestion": "one actionable suggestion or null if safe"
}
```

---

## 2. Development Prompts (Used with AI Coding Assistant)

### Prompt: Generate DNS zone file parser
```
Write a Python function using dnspython to parse a DNS zone file string
and return a list of records with name, ttl, record type, and value fields.
Handle SOA, A, AAAA, CNAME, MX, NS, TXT record types.
```

### Prompt: Generate GitHub PR diff fetcher
```
Write a Python function using PyGithub that takes a GitHub token, repo name,
and PR number, fetches all changed files, and returns for each file:
filename, status (added/modified/removed), patch diff, before content, after content.
```

### Prompt: Generate risk rule engine
```
Write a Python rule engine that takes a list of parsed DNS record changes
and checks them against rules loaded from a YAML config file.
Rules to check: wildcard records, low TTL (< 300s), MX changes, NS changes.
Return list of flagged issues with severity and suggestion.
```

### Prompt: Generate GitHub Actions YAML
```
Write a GitHub Actions workflow YAML that:
1. Triggers on pull_request events for files in zones/ directory
2. Sets up Python 3.10
3. Installs requirements from requirements.txt
4. Installs and starts Ollama with Mistral model
5. Runs python agent/main.py with PR number and repo as env vars
```

### Prompt: Format markdown review comment
```
Write a Python function that takes DNS review results (syntax errors,
rule flags, LLM analysis) and formats them into a structured GitHub
PR review comment in markdown with emojis for severity levels.
Use 🔴 for critical, ⚠️ for warning, ✅ for safe.
```

---

## 3. Testing Prompts

### Prompt: Generate test DNS zone files with risks
```
Generate a DNS zone file for example.com that contains:
1. A wildcard record with TTL of 60 seconds
2. An MX record change
3. A normal safe A record
Use standard BIND zone file format.
```

### Prompt: Generate unit tests
```
Write pytest unit tests for a DNS zone file validator that uses dnspython.
Test cases: valid zone file, missing SOA, missing NS, malformed A record,
invalid IP address, empty zone file.
```

---

*These prompts were used during the Hackathon Round 4 development of IM-08.*
