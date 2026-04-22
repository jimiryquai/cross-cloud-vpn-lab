# Cross-Cloud VPN Lab

This repository contains an Azure Function and supporting assets for secure identifier translation and integration between Azure, AWS Cognito, and a GUID API. It includes production-grade code, robust testing, and CI/CD automation.

## Project Structure

- `src/` — Azure Function app, shared logic, and tests
- `docs/` — Architecture, NFRs, test strategy, and meeting notes

## Key Features

- **Azure Function** for GUID translation and secure API proxying
- **Integration with Azure Key Vault** for secret management
- **AWS Cognito** OAuth token acquisition
- **Comprehensive tests** (unit + integration)
- **CI/CD** with GitLab: linting, security, and tests

## Quick Start

### 1. Clone and Set Up
```bash
# Clone repo
 git clone <repo-url>
 cd cross-cloud-vpn-lab

# Set up Python environment
cd src
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure Environment Variables

Set these for integration tests and production:

| Variable                            | Required | Description                                             | Default                |
|-------------------------------------|----------|---------------------------------------------------------|------------------------|
| `KEY_VAULT_URL`                     | Yes      | Azure Key Vault URL                                     | —                      |
| `COGNITO_DOMAIN`                    | Yes      | AWS Cognito domain (e.g., `my-domain.auth.us-east-1.amazoncognito.com`) | —                      |
| `GUID_API_URL`                      | Yes      | GUID API endpoint base URL                              | —                      |
| `COGNITO_CLIENT_ID_SECRET_NAME`     | No       | Key Vault secret name for Cognito client ID             | `cognito-client-id`    |
| `COGNITO_CLIENT_SECRET_SECRET_NAME` | No       | Key Vault secret name for Cognito client secret         | `cognito-client-secret`|

Optionally, use a `.env` file (not committed):
```
KEY_VAULT_URL=https://<your-vault>.vault.azure.net
COGNITO_DOMAIN=...
GUID_API_URL=...
# Optional overrides:
# COGNITO_CLIENT_ID_SECRET_NAME=custom-client-id
# COGNITO_CLIENT_SECRET_SECRET_NAME=custom-client-secret
```

### 3. Run Tests
```bash
cd src
python -m unittest discover -s tests -v
```

## CI/CD

- See `.gitlab-ci.yml` for pipeline stages: lint, security, and tests
- Environment variables must be set in GitLab CI/CD settings for integration tests

## Documentation
- See `docs/` for architecture, NFRs, and test strategy
- See `src/tests/README.md` for detailed test setup and troubleshooting

- Ensure all code passes lint (Ruff), security, and tests before submitting a merge request
- Run `ruff check src` for linting and `ruff format src` for formatting
- Follow the test strategy in `docs/TEST-STRATEGY.md`

---
# Structured Logging with ContextLogger

This project uses a custom `ContextLogger` to ensure all logs include the `project` and `correlation_id` context for every request. This approach supports traceability and multi-tenant diagnostics.

## Usage

Import and instantiate the logger:

```python
from shared.context_logger import ContextLogger
logger = ContextLogger()
```

Replace standard logging calls with:

```python
logger.info("Message", project=project, correlation_id=correlation_id)
logger.error("Error message", project=project, correlation_id=correlation_id)
```

- `project` should be the current tenant/project identifier (from request params or headers).
- `correlation_id` should be the request's correlation ID (from headers or generated if missing).

## Example Output

```
[project=fqm] [correlation_id=abc123] Processing single GUID lookup.
[project=acs] [correlation_id=xyz789] Proxy Failure: Upstream service returned 500
```

## Why Structured Logging?
- Enables filtering and searching logs by project or correlation ID.
- Supports distributed tracing and debugging in multi-tenant environments.
- Ensures all logs are actionable and traceable to a specific request and tenant.

## Where to Use
- All API route handlers
- Shared modules (e.g., authentication, error handling)
- Any place where logs are emitted for requests or background jobs

## Implementation Details
- See `src/shared/context_logger.py` for implementation.
- All previous `logging.info`, `logging.error`, etc. should be replaced with the context logger for consistency.
