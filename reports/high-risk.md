# DNS Zone Review Bot Report (High Risk)
**Risk Score:** 60/100 (HIGH RISK)

### File: `zones/techcorp.com.txt`
#### Rule-Based Checks
 **HIGH — MX Record Change**
* Record: `@ IN MX 10 mail.techcorp.com.`
* Issue: MX record added or modified; affects all incoming email delivery paths.
* Suggestion: Verify mail server config before merging.
 **HIGH — Critical Service Modification**
* Record: `api 3600 IN A 93.184.216.34`
* Issue: Modification affecting critical service subdomain: 'api'.
* Suggestion: Ensure this change is reviewed by the team lead.

#### AI Risk Analysis (Mistral 7B)
 **HIGH RISK**
* Record: `@ IN MX 10 mail.techcorp.com.`
* Analysis: Changing MX record directs corporate emails. Verify destination server is configured to prevent email loss.
