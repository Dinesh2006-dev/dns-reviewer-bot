# DNS Zone Review Bot Report (Critical Risk)
**Risk Score:** 90/100 (CRITICAL RISK)

### File: `zones/techcorp.com.txt`
#### Rule-Based Checks
 **CRITICAL — Wildcard Record**
* Record: `* 60 IN A 1.2.3.4`
* Issue: Wildcard record added: '*' — exposes ALL subdomains.
* Suggestion: Use explicit subdomain records instead of wildcards.
 **CRITICAL — Private IP Exposure**
* Record: `internal 3600 IN A 10.0.0.5`
* Issue: Private IP address exposed in public DNS: 10.0.0.5.
* Suggestion: Only use public IP addresses in public zone configurations.
 **WARNING — Low TTL**
* Record: `* 60 IN A 1.2.3.4`
* Issue: Very low TTL: 60s (recommended minimum: 300s).
* Suggestion: Increase TTL to at least 300 seconds.
