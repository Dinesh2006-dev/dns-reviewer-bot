import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agent')))

from diff_parser import parse_diff, _parse_record

def test_parse_record_simple_a():
    line = "www 3600 IN A 93.184.216.34"
    res = _parse_record(line)
    assert res["name"] == "www"
    assert res["ttl"] == 3600
    assert res["rclass"] == "IN"
    assert res["rtype"] == "A"
    assert res["value"] == "93.184.216.34"

def test_parse_record_no_ttl_class():
    line = "mail MX 10 mail.example.com."
    res = _parse_record(line)
    assert res["name"] == "mail"
    assert res["ttl"] is None
    assert res["rclass"] == "IN"  # default
    assert res["rtype"] == "MX"
    assert res["value"] == "10 mail.example.com."

def test_parse_diff_added_removed():
    patch = (
        "@@ -1,4 +1,5 @@\n"
        "+*    60    IN    A    1.2.3.4\n"
        "-www       3600    IN    A      93.184.216.34\n"
    )
    changes = parse_diff(patch, "", "")
    assert len(changes) == 2
    
    assert changes[0]["type"] == "added"
    assert changes[0]["record"]["name"] == "*"
    assert changes[0]["record"]["rtype"] == "A"
    assert changes[0]["record"]["ttl"] == 60
    
    assert changes[1]["type"] == "removed"
    assert changes[1]["record"]["name"] == "www"
    assert changes[1]["record"]["rtype"] == "A"
    assert changes[1]["record"]["ttl"] == 3600

def test_parse_diff_ignores_comments_and_headers():
    patch = (
        "--- zones/example.com.txt\n"
        "+++ zones/example.com.txt\n"
        "@@ -1,4 +1,4 @@\n"
        "+; this is a comment and should be skipped\n"
        "+api       3600    IN    A      10.0.0.5\n"
    )
    changes = parse_diff(patch, "", "")
    assert len(changes) == 1
    assert changes[0]["type"] == "added"
    assert changes[0]["record"]["name"] == "api"
