# Azure Function Tests

Real integration tests with AWS services + minimal unit tests for pure logic.

---

## Test Philosophy

**Integration Over Mocks**: Test real AWS services, not mocks.

- ✅ `test_integration.py` - Real AWS Secrets Manager, Cognito, GUID API (90% of tests)
- ✅ `test_unit.py` - Pure token caching logic only (10% of tests)

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
# AWS Credentials
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# AWS Configuration
export AWS_REGION="eu-west-2"
export AWS_SECRET_NAME="consumer/cognito/vpn-lab/credentials"

# Cognito Configuration
export COGNITO_DOMAIN="vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com"

# GUID API Configuration
export GUID_API_URL="https://z3euh2qc03.execute-api.eu-west-2.amazonaws.com/test"
```

**Or use a `.env` file** (not committed):
```bash
# .env file (add to .gitignore)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=eu-west-2
AWS_SECRET_NAME=consumer/cognito/vpn-lab/credentials
COGNITO_DOMAIN=vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com
GUID_API_URL=https://z3euh2qc03.execute-api.eu-west-2.amazonaws.com/test
```

---

## Running Tests

### All Tests

```bash
pytest tests/ -v
```

### Integration Tests Only

```bash
pytest tests/test_integration.py -v
```

### Unit Tests Only

```bash
pytest tests/test_unit.py -v
```

### With Detailed Output

```bash
pytest tests/ -v -s
```

### With Coverage

```bash
pytest tests/ -v --cov=GetGUID --cov-report=html

# Open coverage report
open htmlcov/index.html  # On macOS
xdg-open htmlcov/index.html  # On Linux
```

### Specific Test

```bash
pytest tests/test_integration.py::TestRealAWSIntegration::test_end_to_end_flow -v -s
```

---

## Test Structure

### Integration Tests (`test_integration.py`)

**Real AWS services tested**:
1. AWS Secrets Manager - credential retrieval
2. AWS Cognito - OAuth token acquisition
3. GUID API - person details lookup
4. Token caching - verify reuse
5. Error handling - invalid GUID

**No mocks** - all tests call real AWS endpoints.

### Unit Tests (`test_unit.py`)

**Pure logic tested**:
1. Token cache empty state
2. Token storage with expiration
3. Token retrieval when valid
4. Token expiration detection
5. 60-second safety buffer
6. Token overwrite behavior

**No AWS calls** - just datetime math.

---

## Expected Results

### Integration Tests (6 tests)

```
test_retrieve_credentials_from_real_secrets_manager PASSED
test_get_token_from_real_cognito PASSED
test_call_real_guid_api PASSED
test_end_to_end_flow PASSED
test_token_caching_reduces_cognito_calls PASSED
test_invalid_guid_returns_404 PASSED
```

### Unit Tests (7 tests)

```
test_get_cached_token_returns_none_when_empty PASSED
test_cache_token_stores_with_expiration PASSED
test_get_cached_token_returns_valid_token PASSED
test_get_cached_token_returns_none_when_expired PASSED
test_cache_includes_60_second_buffer PASSED
test_cache_token_overwrites_existing PASSED
test_cache_with_different_expiration_times PASSED
```

---

## Troubleshooting

### Missing Environment Variables

```
SKIPPED - Missing required environment variables: AWS_ACCESS_KEY_ID, ...
```

**Fix**: Set all required environment variables (see Setup section)

### AWS Credentials Invalid

```
ClientError: An error occurred (InvalidClientTokenId) ...
```

**Fix**: Verify AWS credentials are correct

### Cognito Authentication Failed

```
Exception: Cognito authentication failed: 401
```

**Fix**: Check Cognito credentials in Secrets Manager are valid

### GUID API Returns 404

```
Exception: GUID API call failed: 404
```

**Fix**: Verify GUID API is deployed and accessible

---

## CI/CD Integration

See `.github/workflows/test.yml` for automated testing setup.

**GitHub Secrets Required**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `COGNITO_DOMAIN`
- `GUID_API_URL`

---

## Coverage Goals

| Component | Target | Actual |
|-----------|--------|--------|
| Token Caching | 100% | - |
| AWS Integration | 90% | - |
| Error Handling | 85% | - |
| Overall | 90% | - |

Run `pytest --cov` to check actual coverage.

---

## Next Steps

1. Run tests locally to verify setup
2. Fix any failing tests
3. Add more edge case tests if needed
4. Set up CI/CD pipeline
5. Document any new test scenarios

---

**Test Strategy**: See `/docs/TEST-STRATEGY.md` for detailed approach
