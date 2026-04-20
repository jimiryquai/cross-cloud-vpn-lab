
# Azure Team Recommendations for GUID Service Integration

This document provides recommended actions for the Azure/Infra team to ensure the GUID service meets its NFRs and operates reliably in production.

## Infrastructure Recommendations

1. **Enable System-Assigned Managed Identity** for the Azure Function and grant it access to the required Key Vault secrets (Cognito client ID and secret).
2. **Implement a failover plan** for the Azure Function by deploying to both UK South and UK West (Azure paired regions). Use Azure Front Door or Traffic Manager for automatic failover. This ensures compliance with UK government data residency and resilience requirements.
3. **Configure a warm-up strategy** (e.g., Always Ready instances or scheduled ping) to minimize cold start latency for the Azure Function.
4. **Review Azure policies and RBAC** to ensure there are no restrictions that could block the Function's access to Key Vault or outbound calls to AWS.
5. **Configure retry logic** for the Power Platform Custom Connector and/or within the Azure Function to handle transient network errors gracefully.
6. **Set up monitoring and alerting** for both Key Vault and the Azure Function to detect and respond to failures quickly.
7. **Deploy Function and Key Vault in paired UK regions** (UK South and UK West) to minimize network latency and support disaster recovery, in line with UK government best practices.

---

## Heads Up: Proposed Bulk Translation Function

### What we're planning

We want to extend the Azure Function to handle the **data processing** for bulk NINO→GUID translation — not just proxy the API call, but also parse the CSV, extract identifiers, swap the translated values back in, and return the modified CSV.

Currently the Function only does single-record lookups. The upstream AWS GUID service already exposes a bulk API (up to 10,000 records per request), so the API call itself is straightforward. The question is where the **record-level data manipulation** happens: in the Azure Function or in Power Automate.

### Why we recommend doing this in the Function

We could call the bulk API from Power Automate (via the Function as an auth proxy) and then do the row-by-row NINO→GUID replacement in the Flow itself. But for imports of up to 50,000 rows, that means Power Automate would need to:

- Parse the CSV and extract the NINO column
- Build the JSON payload for the bulk API
- Receive the NINO→GUID mapping back
- Loop through every row (`Apply to Each` over 50k items) to swap in the translated values
- Reconstruct the CSV for Dataverse import

That row-by-row manipulation is the problem. `Apply to Each` in Power Automate is sequential and slow — 50k iterations would likely hit flow timeout limits (5 minutes for instant flows, 30 days for automated but with significant throttling). It's also difficult to debug when it fails mid-way through.

In Python, the same operation is a dictionary lookup across a list — it completes in seconds, handles edge cases cleanly (encoding, line endings, quoted fields), and any errors surface in Function logs rather than buried in a flow run history.

### What we need from you

Nothing to action right now — we just want you to be aware this is coming. If there are any concerns about the Function doing this kind of data processing (e.g. hosting plan limits, compute/memory constraints, security policy, network rules), please let us know before we start building.

---

Update and expand these recommendations as implementation progresses.