import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agent')))

from rule_engine import check_rules

def test_safe_record_no_flags():
    changes = [
        {
            "type": "added",
            "raw": "api 3600 IN A 10.0.0.5",
            "record": {
                "name": "api",
                "ttl": 3600,
                "rclass": "IN",
                "rtype": "A",
                "value": "10.0.0.5"
            }
        }
    ]
    flags = check_rules(changes)
    assert len(flags) == 0

def test_wildcard_critical_flag():
    changes = [
        {
            "type": "added",
            "raw": "* 3600 IN A 1.2.3.4",
            "record": {
                "name": "*",
                "ttl": 3600,
                "rclass": "IN",
                "rtype": "A",
                "value": "1.2.3.4"
            }
        }
    ]
    flags = check_rules(changes)
    assert len(flags) == 1
    assert flags[0]["rule"] == "WILDCARD_RECORD"
    assert flags[0]["severity"] == "critical"

def test_low_ttl_warning_flag():
    changes = [
        {
            "type": "added",
            "raw": "www 60 IN A 1.2.3.4",
            "record": {
                "name": "www",
                "ttl": 60,
                "rclass": "IN",
                "rtype": "A",
                "value": "1.2.3.4"
            }
        }
    ]
    flags = check_rules(changes)
    assert len(flags) == 1
    assert flags[0]["rule"] == "LOW_TTL"
    assert flags[0]["severity"] == "warning"

def test_mx_change_high_flag():
    changes = [
        {
            "type": "added",
            "raw": "@ IN MX 10 mail.example.com.",
            "record": {
                "name": "@",
                "ttl": None,
                "rclass": "IN",
                "rtype": "MX",
                "value": "10 mail.example.com."
            }
        }
    ]
    flags = check_rules(changes)
    assert len(flags) == 1
    assert flags[0]["rule"] == "MX_CHANGE"
    assert flags[0]["severity"] == "high"

def test_ns_change_critical_flag():
    changes = [
        {
            "type": "added",
            "raw": "@ IN NS ns3.example.com.",
            "record": {
                "name": "@",
                "ttl": None,
                "rclass": "IN",
                "rtype": "NS",
                "value": "ns3.example.com."
            }
        }
    ]
    flags = check_rules(changes)
    assert len(flags) == 1
    assert flags[0]["rule"] == "NS_CHANGE"
    assert flags[0]["severity"] == "critical"

def test_soa_change_warning_flag():
    changes = [
        {
            "type": "added",
            "raw": "@ IN SOA ns1.example.com. admin.example.com. ( ... )",
            "record": {
                "name": "@",
                "ttl": None,
                "rclass": "IN",
                "rtype": "SOA",
                "value": "ns1.example.com. admin.example.com. ( ... )"
            }
        }
    ]
    flags = check_rules(changes)
    assert len(flags) == 1
    assert flags[0]["rule"] == "SOA_CHANGE"
    assert flags[0]["severity"] == "warning"
