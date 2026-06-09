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
