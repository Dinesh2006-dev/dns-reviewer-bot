"""
DNS Validator — Uses dnspython to validate zone file syntax.
"""

import dns.zone
import dns.exception


def validate_zone(zone_content: str, origin: str = "example.com.") -> list[dict]:
    """
    Parse and validate a DNS zone file string.
    Returns list of syntax errors found.
    """
    errors = []

    if not zone_content.strip():
        return [{"line": 0, "error": "Zone file is empty"}]

    try:
        zone = dns.zone.from_text(
            zone_content,
            origin=origin,
            check_origin=False
        )

        # Check for SOA record
        if zone.get_rdataset("@", "SOA") is None:
            errors.append({"line": 0, "error": "Missing SOA record — required in every zone file"})

        # Check for NS records
        if zone.get_rdataset("@", "NS") is None:
            errors.append({"line": 0, "error": "Missing NS record — required in every zone file"})

    except dns.zone.UnknownOrigin as e:
        errors.append({"line": 0, "error": f"Unknown origin: {e}"})
    except dns.exception.FormError as e:
        errors.append({"line": 0, "error": f"Zone format error: {e}"})
    except Exception as e:
        errors.append({"line": 0, "error": f"Parse error: {e}"})

    return errors
