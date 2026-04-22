# Bulk GUID Translation: Asynchronous Architecture Proposal (Phase 2)

## Context & Current State (Phase 1)
The cross-cloud GUID translation service currently supports a **Synchronous Bulk Proxy** route. This MVP securely maps up to 5,000 records per request, fetches an AWS Cognito OAuth token from Azure Key Vault, and channels the payload directly to the upstream AWS API.

## The Bottleneck
While synchronous processing satisfies immediate latency constraints for typical payloads, 5,000-record batch processing runs the risk of saturating the Azure Function timeout windows or dropping connections if the underlying AWS infrastructure processes the batch too slowly. 

To guarantee strict NFR latency limits on the Azure edge, we propose transitioning the bulk route to an Asynchronous Event-Driven pattern.

## Proposed Asynchronous Flow (Phase 2)

**Requirement:** Azure Infrastructure team to provision a message queuing system (e.g. Azure Service Bus or Event Grids).

1. **Ingestion (Fast ACK):** Client submits the bulk JSON payload. The Azure Function validates the schema (Pydantic), drops the payload onto the Azure Service Bus queue, and *immediately* returns a `202 Accepted` to the client along with an asynchronous Job ID.
2. **Decoupled Processing:** A secondary backend Function App (triggered by the Service Bus queue) picks up the payload. It securely resolves the Cognito token and proxies the request to AWS.
3. **Retrieval/Webhook:** The client either polls a `/status/{jobId}` route or receives the completed payload via a configured Webhook upon batch completion.

### Downstream Implications
This architecture requires **zero architectural changes** from the target AWS API team. The upstream AWS implementation remains a robust REST endpoint, whilst Azure absorbs the asynchronous queueing logic.

## Questions for Azure Infrastructure Team
1. **Queue Tooling**: Is Azure Service Bus the preferred organizational standard for this payload size, or is Azure Event Grid more suitable?
2. **State Management**: Would we utilize Azure Cosmos DB or Table Storage to hold the Job Status IDs before retrieval?
3. **Timeframe**: What is the SLA to provision these resources within our current Azure subscription?
