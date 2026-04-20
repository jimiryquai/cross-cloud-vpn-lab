
# Azure Team Recommendations for GUID Service Integration

This document provides recommended actions for the Azure/Infra team to ensure the GUID service meets its NFRs and operates reliably in production.

## Recommendations

1. **Enable System-Assigned Managed Identity** for the Azure Function and grant it access to the required Key Vault secrets (Cognito client ID and secret).
2. **Implement a failover plan** for the Azure Function by deploying to both UK South and UK West (Azure paired regions). Use Azure Front Door or Traffic Manager for automatic failover. This ensures compliance with UK government data residency and resilience requirements.
3. **Configure a warm-up strategy** (e.g., Always Ready instances or scheduled ping) to minimize cold start latency for the Azure Function.
4. **Review Azure policies and RBAC** to ensure there are no restrictions that could block the Function's access to Key Vault or outbound calls to AWS.
5. **Configure retry logic** for the Power Platform Custom Connector and/or within the Azure Function to handle transient network errors gracefully.
6. **Set up monitoring and alerting** for both Key Vault and the Azure Function to detect and respond to failures quickly.
7. **Deploy Function and Key Vault in paired UK regions** (UK South and UK West) to minimize network latency and support disaster recovery, in line with UK government best practices.

---
Update and expand these recommendations as implementation progresses.