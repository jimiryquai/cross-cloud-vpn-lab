# Azure Function Tests

Integration tests with Azure Key Vault + AWS Cognito/GUID API, plus unit tests for pure caching logic.

---

## Test Philosophy

**Integration Over Mocks**: Test real services for confidence, unit-test pure logic for speed.

- ✅ `test_integration.py` - Real Azure Key Vault, Cognito, GUID API (90% of tests)
- ✅ `test_unit.py` - Token caching, secrets caching, mocked Key Vault (10% of tests)

---

## Setup

### Install Dependencies

```bash
cd azure-function

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install runtime dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r requirements-dev.txt
```

### Set Environment Variables

```bash
# Azure Key Vault (stores Cognito credentials)
export KEY_VAULT_URL="https://<your-vault-name>.vault.azure.net"

# Optional: override default secret names in Key Vault
export COGNITO_CLIENT_ID_SECRET_NAME="cognito-client-id"
export COGNITO_CLIENT_SECRET_SECRET_NAME="cognito-client-secret"

# Cognito Configuration
export COGNITO_DOMAIN="vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com"

# GUID API Configuration
export GUID_API_URL="https://z3euh2qc03.execute-api.eu-west-2.amazonaws.com/test"
```

**Or use a `.env` file** (not committed):
```bash
# .env file (add to .gitignore)
KEY_VAULT_URL=https://<your-vault-name>.vault.azure.net
COGNITO_DOMAIN=vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com
GUID_API_URL=https://z3euh2qc03.execute-api.eu-west-2.amazonaws.com/test
```

> **Note:** Integration tests require `DefaultAzureCredential` to be configured.
> Locally this means either Azure CLI login (`az login`) or setting
> `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` env vars.

---

## Running Tests

### All Tests

```bash
pytest tests/ -v
```

### Unit Tests Only (no external deps)

```bash
pytest tests/test_unit.py -v -s
```

### Integration Tests Only (requires Key Vault + AWS access)

```bash
pytest tests/test_integration.py -v -s
```

### With Coverage

```bash
pytest tests/ -v --cov=GetGUID --cov-report=html

# Open coverage report
xdg-open htmlcov/index.html  # On Linux
```

### Specific Test

```bash
pytest tests/test_integration.py::TestRealIntegration::test_end_to_end_flow -v -s
```

---

## Test Structure

### Integration Tests (`test_integration.py`)

**Real services tested**:
1. Azure Key Vault — Cognito credential retrieval
2. Key Vault credential caching — verify reuse without repeat calls
3. AWS Cognito — OAuth token acquisition
4. GUID API — identifier lookup (raw upstream response)
5. End-to-end — credentials → token → API call
6. Token caching — verify reuse
7. Invalid GUID handling

**No mocks** — all tests call real Azure + AWS endpoints.

### Unit Tests (`test_unit.py`)

**Pure logic tested (no external calls)**:
1. Token cache empty state
2. Token storage with expiration
3. Token retrieval when valid
4. Token expiration detection
5. 60-second safety buffer
6. Token overwrite behavior
7. Secrets cache returns cached values
8. Missing `KEY_VAULT_URL` raises exception
9. Key Vault fetch populates secrets cache (mocked)

---

## Expected Results

### Integration Tests (8 tests)

```
test_retrieve_credentials_from_key_vault PASSED
test_credentials_are_cached_after_first_retrieval PASSED
test_get_token_from_real_cognito PASSED
test_call_real_guid_api PASSED
test_end_to_end_flow PASSED
test_token_caching_reduces_cognito_calls PASSED
test_invalid_guid_returns_response PASSED
test_expired_token_gets_refreshed SKIPPED
```

### Unit Tests (10 tests)

```
test_get_cached_token_returns_none_when_empty PASSED
test_cache_token_stores_with_expiration PASSED
test_get_cached_token_returns_valid_token PASSED
test_get_cached_token_returns_none_when_expired PASSED
test_cache_includes_60_second_buffer PASSED
test_cache_token_overwrites_existing PASSED
test_cache_with_different_expiration_times PASSED
test_secrets_cache_returns_cached_values PASSED
test_get_cognito_credentials_raises_without_key_vault_url PASSED
test_get_cognito_credentials_fetches_and_caches PASSED
```

---

## Troubleshooting

### Missing Environment Variables

```
SKIPPED: Missing required environment variables: KEY_VAULT_URL, COGNITO_DOMAIN, GUID_API_URL
```

**Fix**: Set all required environment variables (see Setup section)

### Azure Key Vault Access Denied

```
azure.core.exceptions.HttpResponseError: ... ForbiddenByPolicy ...
```

**Fix**: Ensure your identity has `Get` secret permission on the Key Vault. If running locally, run `az login` first.

### Cognito Authentication Failed

```
Exception: Cognito authentication failed: 401
```

**Fix**: Check Cognito credentials stored in Key Vault are still valid

### GUID API Returns Error

```
Exception: Upstream service returned 404
```

**Fix**: Verify GUID API is deployed and accessible

---

## CI/CD Integration

See `.github/workflows/test.yml` for automated testing setup.

**GitHub Secrets Required**:
- `KEY_VAULT_URL`
- `AZURE_CLIENT_ID` (service principal for Key Vault access)
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_SECRET`
- `COGNITO_DOMAIN`
- `GUID_API_URL`

---

## Coverage Goals

| Component | Target | Actual |
|-----------|--------|--------|
| Token Caching | 100% | - |
| Secrets Caching | 100% | - |
| Key Vault Integration | 90% | - |
| Error Handling | 85% | - |
| Overall | 90% | - |

Run `pytest --cov` to check actual coverage.

---

**Test Strategy**: See `/docs/TEST-STRATEGY.md` for detailed approach
