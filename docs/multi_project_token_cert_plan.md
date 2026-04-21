# Multi-Project Token and Certificate Handling Plan

## Overview
This document outlines the steps required to update the Azure Function and connector logic to support project-specific authentication, certificate usage, and token caching for outbound calls to AWS API Gateway.

## Goals
- Support multiple projects/teams (e.g., FQM, ACS) with unique credentials.
- Dynamically select the correct certificate/ARN and cache tokens per project.
- Ensure secure and efficient authentication for each project.

## Implementation Steps

### 1. Accept Project/Team Parameter
- Update the connector and Azure Function to accept a project/team identifier (e.g., via header or body parameter).
- Document the expected parameter name and format.

### 2. Fetch Project-Specific ARN/Certificate
- Use the project/team parameter to construct the Key Vault secret name (e.g., `fqm-acm-arn`).
- Fetch the ARN/certificate from Azure Key Vault at runtime.

#### Test Checklist for This Step
- [ ] Function reads the project parameter from the request
- [ ] Constructs the correct Key Vault secret name for each project
- [ ] Fetches the correct ARN/certificate from Key Vault for each allowed project value
- [ ] Handles invalid or missing project values gracefully

### 3. Implement Per-Project Token Cache
- Maintain an in-memory cache (e.g., Python dict) mapping project/team to its current token and expiry.
- On each request:
  - Check if a valid token exists for the project.
  - If not, authenticate using the project’s certificate and cache the new token with its expiry.

### 4. Outbound Call to AWS API Gateway
- Use the project-specific token and certificate when making the outbound call.
- Ensure the correct certificate is attached for mTLS if required.

### 5. Error Handling
- Handle missing/invalid project parameters.
- Handle missing secrets in Key Vault.
- Handle token expiry and refresh logic.

### 6. Documentation & Testing
- Update API and connector documentation to describe the new parameter and authentication flow.
- Add or update tests to cover multi-project scenarios.

## Progress Tracking
- [x] Accept project/team parameter in connector
- [ ] Fetch project-specific ARN/certificate from Key Vault
- [ ] Implement per-project token cache
- [ ] Use correct token/certificate for outbound calls
- [ ] Add error handling for missing/invalid parameters and secrets
- [ ] Update documentation and tests

---

**Update this checklist as each step is completed.**
