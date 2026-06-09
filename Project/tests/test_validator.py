import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dns_validator import validate_zone

VALID_ZONE = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.example.com.
@    IN    NS     ns2.example.com.
www  IN    A      93.184.216.34
"""

MISSING_SOA = """$ORIGIN example.com.
$TTL 3600
@    IN    NS     ns1.example.com.
www  IN    A      93.184.216.34
"""

MISSING_NS = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
www  IN    A      93.184.216.34
"""

MALFORMED_ZONE = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.example.com.
www  IN    A      not-an-ip-address
"""

def test_valid_zone():
    errors = validate_zone(VALID_ZONE)
    assert len(errors) == 0

def test_empty_zone():
    errors = validate_zone("")
    assert len(errors) == 1
    assert errors[0]["line"] == 0
    assert "empty" in errors[0]["error"].lower()

def test_missing_soa():
    errors = validate_zone(MISSING_SOA)
    assert any("SOA" in err["error"] for err in errors)

def test_missing_ns():
    errors = validate_zone(MISSING_NS)
    assert any("NS" in err["error"] for err in errors)

def test_malformed_zone():
    errors = validate_zone(MALFORMED_ZONE)
    assert len(errors) > 0
    assert any("format error" in err["error"].lower() or "parse error" in err["error"].lower() for err in errors)

def test_custom_origin():
    # When using a custom origin, dnspython parses and validates relative to it
    custom_zone = """$ORIGIN custom.org.
$TTL 3600
@    IN    SOA    ns1.custom.org.  admin.custom.org. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.custom.org.
"""
    errors = validate_zone(custom_zone, origin="custom.org.")
    assert len(errors) == 0

CNAME_COEXIST_ZONE = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.example.com.
sub  IN    CNAME  target.example.com.
sub  IN    A      10.0.0.1
"""

DUPLICATE_SPF_ZONE = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.example.com.
@    IN    TXT    "v=spf1 include:_spf.google.com ~all"
@    IN    TXT    "v=spf1 ip4:1.2.3.4 ~all"
"""

MALFORMED_SPF_ZONE = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.example.com.
@    IN    TXT    "v=spf1 ip4:invalid_ip ~all"
"""

VALID_SPF_DMARC_ZONE = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.example.com.
@    IN    TXT    "v=spf1 include:_spf.google.com ~all"
_dmarc IN  TXT    "v=DMARC1; p=reject; rua=mailto:dmarc@example.com"
"""

DMARC_WRONG_NODE_ZONE = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.example.com.
www  IN    TXT    "v=DMARC1; p=reject"
"""

MALFORMED_DMARC_ZONE = """$ORIGIN example.com.
$TTL 3600
@    IN    SOA    ns1.example.com.  admin.example.com. ( 2024010101 3600 900 604800 300 )
@    IN    NS     ns1.example.com.
_dmarc IN  TXT    "v=DMARC1; p=invalid_policy"
"""

def test_cname_coexistence():
    errors = validate_zone(CNAME_COEXIST_ZONE)
    assert len(errors) == 1
    assert "CNAME record coexisting with other record types" in errors[0]["error"]
    assert errors[0]["line"] > 0

def test_duplicate_spf():
    errors = validate_zone(DUPLICATE_SPF_ZONE)
    assert len(errors) == 1
    assert "Multiple SPF records on a single host are invalid" in errors[0]["error"]
    assert errors[0]["line"] > 0

def test_malformed_spf():
    errors = validate_zone(MALFORMED_SPF_ZONE)
    assert len(errors) == 1
    assert "Invalid SPF record syntax" in errors[0]["error"]
    assert "Invalid IPv4 address" in errors[0]["error"]
    assert errors[0]["line"] > 0

def test_valid_spf_dmarc():
    errors = validate_zone(VALID_SPF_DMARC_ZONE)
    assert len(errors) == 0

def test_dmarc_wrong_node():
    errors = validate_zone(DMARC_WRONG_NODE_ZONE)
    assert len(errors) == 1
    assert "DMARC policy found on node" in errors[0]["error"]
    assert "must be placed on a node named '_dmarc'" in errors[0]["error"]
    assert errors[0]["line"] > 0

def test_malformed_dmarc():
    errors = validate_zone(MALFORMED_DMARC_ZONE)
    assert len(errors) == 1
    assert "Invalid DMARC record syntax" in errors[0]["error"]
    assert "must be none, quarantine, or reject" in errors[0]["error"]
    assert errors[0]["line"] > 0

