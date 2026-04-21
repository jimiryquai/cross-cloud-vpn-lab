# Cross-Cloud VPN Lab

This repository contains an Azure Function and supporting assets for secure identifier translation and integration between Azure, AWS Cognito, and a GUID API. It includes production-grade code, robust testing, and CI/CD automation.

## Project Structure

- `azure-function/` — Azure Function app, shared logic, and tests
- `docs/` — Architecture, NFRs, test strategy, and meeting notes
- `power-platform/` — Power Platform connectors and solution files
- `Workflows/` — Workflow definitions

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
cd azure-function
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure Environment Variables
Set these for integration tests and production:
- `KEY_VAULT_URL` — Azure Key Vault URL
- `COGNITO_DOMAIN` — AWS Cognito domain
- `GUID_API_URL` — GUID API endpoint

Optionally, use a `.env` file (not committed):
```
KEY_VAULT_URL=https://<your-vault>.vault.azure.net
COGNITO_DOMAIN=...
GUID_API_URL=...
```

### 3. Run Tests
```bash
cd azure-function
python -m unittest discover -s tests -v
```

## CI/CD

- See `.gitlab-ci.yml` for pipeline stages: lint, security, and tests
- Environment variables must be set in GitLab CI/CD settings for integration tests

## Documentation
- See `docs/` for architecture, NFRs, and test strategy
- See `azure-function/tests/README.md` for detailed test setup and troubleshooting

## Contributing
- Ensure all code passes lint, security, and tests before submitting a merge request
- Follow the test strategy in `docs/TEST-STRATEGY.md`

---
