import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agent')))

from rule_engine import check_rules

def test_safe_record_no_flags():
    changes = [
        {
            "type": "added",
            "raw": "blog 3600 IN A 93.184.216.34",
            "record": {
                "name": "blog",
                "ttl": 3600,
                "rclass": "IN",
                "rtype": "A",
                "value": "93.184.216.34"
            }
        }
    ]
    flags = check_rules(changes)
    assert len(flags) == 0

def test_wildcard_critical_flag():
    changes = [
        {
            "type": "added",
            "raw": "* 3600 IN A 93.184.216.34",
            "record": {
                "name": "*",
                "ttl": 3600,
                "rclass": "IN",
                "rtype": "A",
                "value": "93.184.216.34"
            }
        }
    ]
    flags = check_rules(changes)
    assert any(f["rule"] == "WILDCARD_RECORD" for f in flags)

def test_low_ttl_warning_flag():
    changes = [
        {
            "type": "added",
            "raw": "www 60 IN A 93.184.216.34",
            "record": {
                "name": "www",
                "ttl": 60,
                "rclass": "IN",
                "rtype": "A",
                "value": "93.184.216.34"
            }
        }
    ]
    flags = check_rules(changes)
    assert any(f["rule"] == "LOW_TTL" for f in flags)

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
    assert any(f["rule"] == "MX_CHANGE" for f in flags)

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
    assert any(f["rule"] == "NS_CHANGE" for f in flags)

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
    assert any(f["rule"] == "SOA_CHANGE" for f in flags)

def test_private_ip_exposure_flag():
    changes = [
        {
            "type": "added",
            "raw": "dev 3600 IN A 192.168.1.10",
            "record": {
                "name": "dev",
                "ttl": 3600,
                "rclass": "IN",
                "rtype": "A",
                "value": "192.168.1.10"
            }
        }
    ]
    flags = check_rules(changes)
    assert any(f["rule"] == "PRIVATE_IP_EXPOSURE" for f in flags)

def test_critical_service_change_flag():
    changes = [
        {
            "type": "added",
            "raw": "payment 3600 IN A 93.184.216.34",
            "record": {
                "name": "payment",
                "ttl": 3600,
                "rclass": "IN",
                "rtype": "A",
                "value": "93.184.216.34"
            }
        }
    ]
    flags = check_rules(changes)
    assert any(f["rule"] == "CRITICAL_SERVICE_CHANGE" for f in flags)

def test_critical_record_removal_flag():
    changes = [
        {
            "type": "removed",
            "raw": "www 3600 IN A 93.184.216.34",
            "record": {
                "name": "www",
                "ttl": 3600,
                "rclass": "IN",
                "rtype": "A",
                "value": "93.184.216.34"
            }
        }
    ]
    flags = check_rules(changes)
    assert any(f["rule"] == "CRITICAL_RECORD_REMOVAL" for f in flags)

def test_mass_deletion_flag():
    # Simulate deleting 5 records
    changes = [
        {"type": "removed", "raw": f"host{i} 3600 IN A 93.184.216.34", "record": {"name": f"host{i}", "rtype": "A"}}
        for i in range(5)
    ]
    flags = check_rules(changes)
    assert any(f["rule"] == "MASS_DELETION" for f in flags)

def test_record_modification_does_not_trigger_removal_flag():
    # Simulate a modification (removal + addition of the same record name and type)
    changes = [
        {
            "type": "removed",
            "raw": "mail 3600 IN A 10.0.0.10",
            "record": {
                "name": "mail",
                "ttl": 3600,
                "rclass": "IN",
                "rtype": "A",
                "value": "10.0.0.10"
            }
        },
        {
            "type": "added",
            "raw": "mail 3600 IN A 10.0.0.11",
            "record": {
                "name": "mail",
                "ttl": 3600,
                "rclass": "IN",
                "rtype": "A",
                "value": "10.0.0.11"
            }
        }
    ]
    flags = check_rules(changes)
    # CRITICAL_RECORD_REMOVAL should not trigger
    assert not any(f["rule"] == "CRITICAL_RECORD_REMOVAL" for f in flags)
    # CRITICAL_SERVICE_CHANGE should trigger exactly once (not twice)
    service_changes = [f for f in flags if f["rule"] == "CRITICAL_SERVICE_CHANGE"]
    assert len(service_changes) == 1
