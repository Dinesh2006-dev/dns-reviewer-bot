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

    # Map the added record keys (name, rtype) to identify modifications
    added_keys = {
        (c["record"].get("name"), c["record"].get("rtype"))
        for c in changes if c["type"] == "added"
    }

    for change in changes:
        record = change.get("record", {})
        rtype  = record.get("rtype", "")
        name   = record.get("name", "")
        ttl    = record.get("ttl")
        value  = record.get("value", "")

        # Determine if this removal is part of an update/modification
        is_modification = (name, rtype) in added_keys

        # Rule 1: Wildcard record
        if name.startswith("*") and change["type"] == "added":
            flags.append({
                "change": change["raw"],
                "rule": "WILDCARD_RECORD",
                "severity": "critical",
                "message": f"A wildcard record ({name}) has been added. Wildcard records automatically resolve any unconfigured subdomains, which increases the attack surface by making the zone vulnerable to subdomain takeovers and DNS recon profiling.",
                "suggestion": "Identify the specific subdomains that require resolution and create explicit host records (A, AAAA, or CNAME) for them. Remove the wildcard record to maintain a secure and deterministic DNS namespace.",
            })

        # Rule 2: Low TTL
        min_ttl = rules.get("min_ttl", 300)
        if ttl is not None and ttl < min_ttl and change["type"] == "added":
            flags.append({
                "change": change["raw"],
                "rule": "LOW_TTL",
                "severity": "warning",
                "message": f"A low Time-To-Live (TTL) of {ttl} seconds was configured (recommended minimum threshold is {min_ttl} seconds). Low TTLs increase the query volume to authoritative name servers, potentially increasing latency and DNS hosting costs, and making the zone more susceptible to denial-of-service (DoS) amplification.",
                "suggestion": f"Increase the TTL to a standard value of at least {min_ttl} seconds (or 3600 seconds for stable records) unless this is a temporary record undergoing active migration or dynamic failover routing.",
            })

        # Rule 3: MX record change
        if rtype == "MX":
            flags.append({
                "change": change["raw"],
                "rule": "MX_CHANGE",
                "severity": "high",
                "message": f"An MX (Mail Exchanger) record has been {change['type']}. Changes to MX records immediately alter inbound email routing paths for the entire domain, which can cause email delivery failures or allow mail interception if misconfigured.",
                "suggestion": "Verify that the target mail servers are fully configured, authenticated (SPF, DKIM, DMARC), and ready to accept traffic. Perform a pre-flight SMTP connection check before applying this change in production.",
            })

        # Rule 4: NS record change
        if rtype == "NS":
            flags.append({
                "change": change["raw"],
                "rule": "NS_CHANGE",
                "severity": "critical",
                "message": f"A Name Server (NS) record has been {change['type']}. NS records define the authoritative servers for this zone. Modifying these records shifts DNS delegation and can lead to a complete zone outage if the new servers do not host a matching, active copy of the zone file.",
                "suggestion": "Coordinate with the registered domain registrar, verify that the new authoritative name servers are fully synced, online, and responding to queries for this zone, and ensure that zone transfers or records have been completely duplicated to the new hosts.",
            })

        # Rule 5: SOA change
        if rtype == "SOA":
            flags.append({
                "change": change["raw"],
                "rule": "SOA_CHANGE",
                "severity": "warning",
                "message": "The Start of Authority (SOA) record was modified. If the serial number is not incremented, secondary (slave) name servers will not detect the change, resulting in replication lag or out-of-sync zone propagation across global resolvers.",
                "suggestion": "Ensure the SOA serial number is incremented. It is recommended to use the standard YYYYMMDDNN format (where YYYYMMDD is today's date and NN is a 2-digit daily revision counter starting at 01).",
            })

        # Rule 6: Critical Record Removal
        critical_removed = rules.get("critical_if_removed", ["NS", "SOA", "A"])
        if change["type"] == "removed" and rtype in critical_removed:
            if not is_modification:
                flags.append({
                    "change": change["raw"],
                    "rule": "CRITICAL_RECORD_REMOVAL",
                    "severity": "critical" if rtype in ("NS", "SOA") else "high",
                    "message": f"A critical authoritative record of type {rtype} ({name}) was deleted. Removing core root records (like A, NS, or SOA) will result in immediate resolution failures for client requests and disrupt all dependent web and API services.",
                    "suggestion": f"Confirm that the service associated with this host has been successfully retired or migrated to another endpoint, and verify that no active systems or clients are still resolving this record before final approval.",
                })

        # Rule 8: Private IP Exposure
        if change["type"] == "added" and rtype in ("A", "AAAA") and is_private_ip(value):
            flags.append({
                "change": change["raw"],
                "rule": "PRIVATE_IP_EXPOSURE",
                "severity": "critical",
                "message": f"A private RFC 1918 IP address ({value}) was exposed in a public zone record ({name}). Publishing private subnet addresses in public DNS leaks internal network topology, assists attackers in reconnaissance, and violates public naming standards.",
                "suggestion": "Verify if this record is intended for internal DNS resolution only. If so, move it to a private split-horizon DNS zone. If it must remain public, replace the private IP address with a public-facing load balancer, NAT gateway, or proxy IP address.",
            })

        # Rule 10: Critical Service Protection
        critical_services = rules.get("critical_services", ["api", "auth", "payment", "mail"])
        name_part = name.split('.')[0] if '.' in name else name
        if name_part in critical_services:
            # Avoid duplicate warning logs by only firing once per modification (on the added step)
            if change["type"] == "added" or (change["type"] == "removed" and not is_modification):
                flags.append({
                    "change": change["raw"],
                    "rule": "CRITICAL_SERVICE_CHANGE",
                    "severity": "high",
                    "message": f"A record affecting a critical service subdomain ('{name}') was modified or deleted. Critical subdomains (such as api, auth, payment, and mail) handle core business functions and transactions, and changes here present a high risk of business-critical service disruptions.",
                    "suggestion": "Request a peer review and double-signoff from the Infrastructure or DevOps team lead. Validate the target endpoint in a staging environment to ensure full service compatibility before merging.",
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
            "message": f"A mass deletion event was detected: {removals} records were removed in this update, exceeding the threshold limit of {mass_del_limit}. Large bulk deletions could indicate a misconfiguration or accidental truncation.",
            "suggestion": "Conduct a thorough audit of the deleted records to confirm they are no longer in use by any internal or external systems. Verify that this was not caused by an accidental copy-paste or parsing error.",
        })

    mass_create_limit = rules.get("mass_creation_threshold", 10)
    if additions >= mass_create_limit:
        flags.append({
            "change": f"{additions} records added",
            "rule": "MASS_CREATION",
            "severity": "warning",
            "message": f"A mass record addition event was detected: {additions} records were added in this update, exceeding the threshold limit of {mass_create_limit}. Bulk additions should be verified to prevent DNS record bloat or unintended delegation.",
            "suggestion": "Confirm that all newly added records are valid, correctly formatted, and intended for this deployment. Verify that the batch script or tool used to generate these records operated correctly.",
        })

    return flags
