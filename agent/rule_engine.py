"""
Rule Engine — Applies configurable DNS risk rules to detected changes.
"""

import yaml
import os
import ipaddress


RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules", "dns_rules.yaml")


def load_rules() -> dict:
    with open(RULES_PATH, "r") as f:
        return yaml.safe_load(f)


def is_private_ip(ip_str: str) -> bool:
    try:
        # Check if the string is a valid private IPv4/IPv6 address
        ip = ipaddress.ip_address(ip_str.strip())
        return ip.is_private
    except ValueError:
        return False


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

        # Rule 6: Critical Record Removal
        critical_removed = rules.get("critical_if_removed", ["NS", "SOA", "A"])
        if change["type"] == "removed" and rtype in critical_removed:
            flags.append({
                "change": change["raw"],
                "rule": "CRITICAL_RECORD_REMOVAL",
                "severity": "critical" if rtype in ("NS", "SOA") else "high",
                "message": f"Removal of critical record type: {rtype} ({name}) — can cause immediate service outage.",
                "suggestion": f"Verify this removal will not cause an outage for {name}.",
            })

        # Rule 8: Private IP Exposure
        if change["type"] == "added" and rtype in ("A", "AAAA") and is_private_ip(value):
            flags.append({
                "change": change["raw"],
                "rule": "PRIVATE_IP_EXPOSURE",
                "severity": "critical",
                "message": f"Private IP address exposed in public DNS: {value} ({name}).",
                "suggestion": "Only use public IP addresses in public zone configurations.",
            })

        # Rule 10: Critical Service Protection
        critical_services = rules.get("critical_services", ["api", "auth", "payment", "mail"])
        name_part = name.split('.')[0] if '.' in name else name
        if name_part in critical_services:
            flags.append({
                "change": change["raw"],
                "rule": "CRITICAL_SERVICE_CHANGE",
                "severity": "high",
                "message": f"Modification or removal affecting critical service subdomain: '{name}'",
                "suggestion": "Ensure this change has been double-checked by the team lead.",
            })

    # Rule 11 & 12: Mass Deletions & Additions
    additions = sum(1 for c in changes if c["type"] == "added")
    removals = sum(1 for c in changes if c["type"] == "removed")

    mass_del_limit = rules.get("mass_deletion_threshold", 5)
    if removals >= mass_del_limit:
        flags.append({
            "change": f"{removals} records deleted",
            "rule": "MASS_DELETION",
            "severity": "high",
            "message": f"Mass deletion detected: {removals} records removed (limit: {mass_del_limit})",
            "suggestion": "Double check that all deleted records are no longer in use.",
        })

    mass_create_limit = rules.get("mass_creation_threshold", 10)
    if additions >= mass_create_limit:
        flags.append({
            "change": f"{additions} records added",
            "rule": "MASS_CREATION",
            "severity": "warning",
            "message": f"Mass record creation detected: {additions} records added (limit: {mass_create_limit})",
            "suggestion": "Verify this is not a DNS spam or bulk misconfiguration.",
        })

    return flags
