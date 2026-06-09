"""
Diff Parser — Identifies added, removed, and modified DNS records from a PR diff.
"""


def parse_diff(patch: str, before: str, after: str) -> list[dict]:
    """
    Parse git diff patch to extract individual DNS record changes.
    Returns list of change dicts with type, record, and raw line.
    """
    changes = []

    if not patch:
        return changes

    for line in patch.splitlines():
        # Skip diff headers
        if line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
            continue
        # Skip comments and blank lines
        stripped = line[1:].strip() if line and line[0] in ('+', '-') else line.strip()
        if not stripped or stripped.startswith(";"):
            continue

        if line.startswith("+"):
            changes.append({
                "type": "added",
                "raw": stripped,
                "record": _parse_record(stripped),
            })
        elif line.startswith("-"):
            changes.append({
                "type": "removed",
                "raw": stripped,
                "record": _parse_record(stripped),
            })

    return changes


def _parse_record(line: str) -> dict:
    """
    Parse a DNS record line into its components.
    Handles: name TTL class type value
    """
    parts = line.split()
    record = {"name": "", "ttl": None, "rclass": "IN", "rtype": "", "value": ""}

    if not parts:
        return record

    idx = 0
    record["name"] = parts[idx]; idx += 1

    # TTL (numeric)
    if idx < len(parts) and parts[idx].isdigit():
        record["ttl"] = int(parts[idx]); idx += 1

    # Class (IN, CH, HS)
    if idx < len(parts) and parts[idx].upper() in ("IN", "CH", "HS"):
        record["rclass"] = parts[idx].upper(); idx += 1

    # Record type
    if idx < len(parts):
        record["rtype"] = parts[idx].upper(); idx += 1

    # Value (rest of line)
    if idx < len(parts):
        record["value"] = " ".join(parts[idx:])

    return record
