"""
DNS Validator — Uses dnspython to validate zone file syntax and apply standards-compliance checks.
"""

import dns.zone
import dns.exception
import dns.rdatatype
import ipaddress


def find_line_number(zone_content: str, name_str: str, rtype_str: str) -> int:
    """Helper to locate the line number of a record in the zone file."""
    lines = zone_content.splitlines()
    for idx, line in enumerate(lines, 1):
        clean_line = line.strip().lower()
        if not clean_line or clean_line.startswith(";"):
            continue
        tokens = clean_line.split()
        if name_str.lower() in tokens and rtype_str.lower() in tokens:
            return idx
    return 0


def validate_spf_record(spf: str) -> str | None:
    """Validate SPF record syntax and common configuration issues (RFC 7208)."""
    terms = spf.split()
    if not terms:
        return "Record is empty"
    if terms[0] != "v=spf1":
        return "Must start with 'v=spf1'"
    
    has_all = False
    has_redirect = False
    
    for term in terms[1:]:
        # Strip qualifier if present (+, -, ~, ?)
        if term[0] in "+-~?":
            term = term[1:]
        
        if term == "all":
            if has_all:
                return "Duplicate 'all' mechanism"
            has_all = True
        elif term.startswith("include:"):
            if not term.split(":", 1)[1]:
                return "Empty 'include' mechanism"
        elif term.startswith("ip4:"):
            ip_val = term.split(":", 1)[1]
            if not ip_val:
                return "Empty 'ip4' mechanism"
            if "/" in ip_val:
                ip_val, cidr = ip_val.split("/", 1)
                if not cidr.isdigit() or not (0 <= int(cidr) <= 32):
                    return f"Invalid CIDR prefix length in '{term}'"
            try:
                ipaddress.IPv4Address(ip_val)
            except ValueError:
                return f"Invalid IPv4 address in '{term}'"
        elif term.startswith("ip6:"):
            ip_val = term.split(":", 1)[1]
            if not ip_val:
                return "Empty 'ip6' mechanism"
            if "/" in ip_val:
                ip_val, cidr = ip_val.split("/", 1)
                if not cidr.isdigit() or not (0 <= int(cidr) <= 128):
                    return f"Invalid CIDR prefix length in '{term}'"
            try:
                ipaddress.IPv6Address(ip_val)
            except ValueError:
                return f"Invalid IPv6 address in '{term}'"
        elif term == "a" or term.startswith("a:") or term.startswith("a/"):
            pass
        elif term == "mx" or term.startswith("mx:") or term.startswith("mx/"):
            pass
        elif term == "ptr" or term.startswith("ptr:"):
            pass
        elif term.startswith("exists:"):
            pass
        elif term.startswith("redirect="):
            if has_redirect:
                return "Duplicate 'redirect' modifier"
            has_redirect = True
            if not term.split("=", 1)[1]:
                return "Empty 'redirect' modifier"
        elif term.startswith("exp="):
            if not term.split("=", 1)[1]:
                return "Empty 'exp' modifier"
        else:
            return f"Unknown term '{term}'"
            
    if not has_all and not has_redirect:
        return "Missing fallback action ('all' or 'redirect' modifier)"
        
    return None


def validate_dmarc_record(dmarc: str) -> str | None:
    """Validate DMARC record syntax and policy tags (RFC 7489)."""
    parts = [p.strip() for p in dmarc.split(";") if p.strip()]
    if not parts:
        return "Record is empty"
    
    if not parts[0].startswith("v=DMARC1"):
        return "First tag must be 'v=DMARC1'"
        
    tags = {}
    for part in parts:
        if "=" not in part:
            if part == "v=DMARC1":
                continue
            return f"Invalid tag-value pair format in '{part}'"
        tag_key, tag_val = part.split("=", 1)
        tag_key = tag_key.strip().lower()
        tag_val = tag_val.strip().lower()
        tags[tag_key] = tag_val
        
    if "p" not in tags:
        return "Missing required policy tag ('p')"
        
    valid_policies = {"none", "quarantine", "reject"}
    if tags["p"] not in valid_policies:
        return f"Invalid policy '{tags['p']}' (must be none, quarantine, or reject)"
        
    if "sp" in tags and tags["sp"] not in valid_policies:
        return f"Invalid subdomain policy '{tags['sp']}'"
        
    if "fo" in tags:
        fo_opts = set(tags["fo"].split(":"))
        valid_fo = {"0", "1", "d", "s"}
        if not fo_opts.issubset(valid_fo):
            return f"Invalid failure reporting options 'fo={tags['fo']}'"
            
    if "pct" in tags:
        if not tags["pct"].isdigit() or not (0 <= int(tags["pct"]) <= 100):
            return f"Invalid percentage value 'pct={tags['pct']}' (must be 0-100)"
            
    return None


def validate_zone(zone_content: str, origin: str = "example.com.") -> list[dict]:
    """
    Parse and validate a DNS zone file string using dnspython,
    running syntax and semantic validation checks.
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

        # Node-by-node validation
        for name, node in zone.items():
            name_str = name.to_text(omit_final_dot=True)
            rdatasets = node.rdatasets

            # 1. CNAME Coexistence Check (RFC 1034 section 3.6.2)
            has_cname = any(rds.rdtype == dns.rdatatype.CNAME for rds in rdatasets)
            if has_cname:
                allowed_coexist = {
                    dns.rdatatype.CNAME,
                    dns.rdatatype.RRSIG,
                    dns.rdatatype.NSEC,
                    dns.rdatatype.NSEC3,
                    dns.rdatatype.KEY,
                    dns.rdatatype.DS
                }
                other_types = [
                    dns.rdatatype.to_text(rds.rdtype)
                    for rds in rdatasets if rds.rdtype not in allowed_coexist
                ]
                if other_types:
                    line_num = find_line_number(zone_content, name_str, "CNAME")
                    errors.append({
                        "line": line_num,
                        "error": f"Node '{name_str}' contains a CNAME record coexisting with other record types ({', '.join(other_types)}), violating RFC 1034."
                    })

            # 2. SPF Validation
            txt_rds = zone.get_rdataset(name, "TXT")
            if txt_rds:
                spf_records = []
                for rd in txt_rds:
                    txt_val = "".join(s.decode("utf-8", errors="ignore") for s in rd.strings)
                    if txt_val.startswith("v=spf1"):
                        spf_records.append(txt_val)
                
                if len(spf_records) > 1:
                    line_num = find_line_number(zone_content, name_str, "TXT")
                    errors.append({
                        "line": line_num,
                        "error": f"Node '{name_str}' has {len(spf_records)} SPF records. Multiple SPF records on a single host are invalid under RFC 7208."
                    })
                elif len(spf_records) == 1:
                    spf_err = validate_spf_record(spf_records[0])
                    if spf_err:
                        line_num = find_line_number(zone_content, name_str, "TXT")
                        errors.append({
                            "line": line_num,
                            "error": f"Invalid SPF record syntax on '{name_str}': {spf_err}"
                        })

            # 3. DMARC Validation
            is_dmarc_node = (name_str == "_dmarc" or name_str.endswith("._dmarc"))
            
            # Check for TXT records starting with v=DMARC1
            for rds in rdatasets:
                if rds.rdtype == dns.rdatatype.TXT:
                    for rd in rds:
                        txt_val = "".join(s.decode("utf-8", errors="ignore") for s in rd.strings)
                        if txt_val.startswith("v=DMARC1"):
                            if not is_dmarc_node:
                                line_num = find_line_number(zone_content, name_str, "TXT")
                                errors.append({
                                    "line": line_num,
                                    "error": f"DMARC policy found on node '{name_str}', but it must be placed on a node named '_dmarc' or ending with '._dmarc'."
                                })
                            else:
                                dmarc_err = validate_dmarc_record(txt_val)
                                if dmarc_err:
                                    line_num = find_line_number(zone_content, name_str, "TXT")
                                    errors.append({
                                        "line": line_num,
                                        "error": f"Invalid DMARC record syntax on '{name_str}': {dmarc_err}"
                                    })

    except dns.zone.UnknownOrigin as e:
        errors.append({"line": 0, "error": f"Unknown origin: {e}"})
    except dns.exception.FormError as e:
        errors.append({"line": 0, "error": f"Zone format error: {e}"})
    except Exception as e:
        err_msg = str(e)
        if "is not compatible with a CNAME node" in err_msg:
            line_num = 0
            lines = zone_content.splitlines()
            for idx, line in enumerate(lines, 1):
                if "cname" in line.lower() and not line.strip().startswith(";"):
                    line_num = idx
                    break
            errors.append({
                "line": line_num,
                "error": f"CNAME record coexisting with other record types: {err_msg}"
            })
        else:
            errors.append({"line": 0, "error": f"Parse error: {e}"})

    return errors
