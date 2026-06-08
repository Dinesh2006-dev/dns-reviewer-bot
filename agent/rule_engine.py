"""
Rule Engine — Applies configurable DNS risk rules to detected changes.
"""

import yaml
import os


RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules", "dns_rules.yaml")


def load_rules() -> dict:
    with open(RULES_PATH, "r") as f:
        return yaml.safe_load(f)


def check_rules(changes: list[dict]) -> list[dict]:
    """
    Apply risk rules to each DNS record change.
    Returns list of flagged issues with severity and explanation.
    """
    rules = load_rules()
    flags = []

    for change in changes:
        record = change.get("record", {})
        rtype  = record.get("rtype", "")
        name   = record.get("name", "")
        ttl    = record.get("ttl")
        value  = record.get("value", "")

        # Rule 1: Wildcard record
        if name.startswith("*") and change["type"] == "added":
            flags.append({
                "change": change["raw"],
                "rule": "WILDCARD_RECORD",
                "severity": "critical",
                "message": f"Wildcard record added: '{name}' — exposes ALL subdomains.",
                "suggestion": "Use explicit subdomain records instead of wildcards.",
            })

        # Rule 2: Low TTL
        min_ttl = rules.get("min_ttl", 300)
        if ttl is not None and ttl < min_ttl and change["type"] == "added":
            flags.append({
                "change": change["raw"],
                "rule": "LOW_TTL",
                "severity": "warning",
                "message": f"Very low TTL: {ttl}s (recommended minimum: {min_ttl}s).",
                "suggestion": f"Increase TTL to at least {min_ttl} seconds.",
            })

        # Rule 3: MX record change
        if rtype == "MX":
            flags.append({
                "change": change["raw"],
                "rule": "MX_CHANGE",
                "severity": "high",
                "message": f"MX record {change['type']}: affects all inbound email routing.",
                "suggestion": "Verify mail server is ready before merging.",
            })

        # Rule 4: NS record change
        if rtype == "NS":
            flags.append({
                "change": change["raw"],
                "rule": "NS_CHANGE",
                "severity": "critical",
                "message": f"NS record {change['type']}: changes DNS authority for the zone.",
                "suggestion": "Coordinate with DNS registrar before changing NS records.",
            })

        # Rule 5: SOA change
        if rtype == "SOA":
            flags.append({
                "change": change["raw"],
                "rule": "SOA_CHANGE",
                "severity": "warning",
                "message": "SOA record modified — ensure serial number is incremented.",
                "suggestion": "SOA serial must always increase (use YYYYMMDDNN format).",
            })

    return flags
