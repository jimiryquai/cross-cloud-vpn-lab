# Test Strategy - Real Integration Testing

Focus on integration tests with real AWS services. Minimal unit tests only for pure logic.

---

## Philosophy

**Integration Over Mocks**: The Azure Function's purpose is orchestrating AWS services. Test the real integration, not mocks.

**Test What Matters**:
- ✅ Does it work with real AWS Secrets Manager?
- ✅ Does it work with real AWS Cognito?
- ✅ Does it work with the real GUID API?
- ✅ Does token caching logic work correctly?

**Skip What Doesn't**:
- ❌ Mocking AWS SDK calls
- ❌ Mocking HTTP requests
- ❌ Testing that mocks were called correctly

---

## Test Structure

### 1. Integration Tests (Primary - 90% of testing effort)

**File**: `azure-function/tests/test_integration.py`

```python
import pytest
import os
import json
from GetGUID import (
    get_cognito_credentials,
    get_cognito_token,
    call_guid_api,
    get_cached_token,
    cache_token
)

class TestRealAWSIntegration:
    """Integration tests with real AWS services"""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Ensure AWS environment variables are set"""
        required = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_REGION',
            'AWS_SECRET_NAME',
            'COGNITO_DOMAIN',
            'GUID_API_URL'
        ]
        for var in required:
            assert os.environ.get(var), f"{var} must be set for integration tests"

    def test_retrieve_credentials_from_real_secrets_manager(self):
        """Test retrieving Cognito credentials from real AWS Secrets Manager"""
        client_id, secret = get_cognito_credentials()

        # Verify we got real credentials
        assert client_id is not None
        assert secret is not None
        assert len(client_id) > 0
        assert len(secret) > 0
        print(f"✓ Retrieved credentials from Secrets Manager")

    def test_get_token_from_real_cognito(self):
        """Test getting OAuth token from real AWS Cognito"""
        # Get real credentials
        client_id, secret = get_cognito_credentials()

        # Get real OAuth token
        access_token = get_cognito_token(client_id, secret)

        # Verify token
        assert access_token is not None
        assert len(access_token) > 100  # JWT tokens are long
        assert access_token.startswith('eyJ')  # JWT format
        print(f"✓ Got OAuth token from Cognito")

    def test_call_real_guid_api(self):
        """Test calling real GUID API with Bearer token"""
        # Get real credentials and token
        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)

        # Call real API
        test_guid = "123e4567-e89b-12d3-a456-426614174000"
        person_data = call_guid_api(access_token, test_guid)

        # Verify response
        assert person_data is not None
        assert 'nino' in person_data
        assert 'guid' in person_data
        assert person_data['guid'] == test_guid
        print(f"✓ Retrieved person data from GUID API: NINO={person_data['nino']}")

    def test_end_to_end_flow(self):
        """Test complete end-to-end flow with all real services"""
        test_guid = "123e4567-e89b-12d3-a456-426614174000"

        # Step 1: Get credentials from Secrets Manager
        client_id, secret = get_cognito_credentials()
        assert client_id and secret

        # Step 2: Get OAuth token from Cognito
        access_token = get_cognito_token(client_id, secret)
        assert access_token

        # Step 3: Call GUID API
        person_data = call_guid_api(access_token, test_guid)
        assert person_data['nino'] == 'AB123456C'

        print(f"✓ Complete end-to-end flow successful")

    def test_token_caching_reduces_cognito_calls(self):
        """Verify token is cached and reused"""
        client_id, secret = get_cognito_credentials()

        # First call - should get new token
        token1 = get_cognito_token(client_id, secret)

        # Second call - should use cached token (check logs)
        token2 = get_cognito_token(client_id, secret)

        # Tokens should be identical (same cached token)
        assert token1 == token2
        print(f"✓ Token caching working (reused token)")

    def test_invalid_guid_returns_404(self):
        """Test error handling with invalid GUID"""
        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)

        # Call with invalid GUID
        invalid_guid = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(Exception) as exc_info:
            call_guid_api(access_token, invalid_guid)

        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()
        print(f"✓ Correctly handled invalid GUID (404)")

    def test_expired_token_gets_refreshed(self):
        """Test token refresh when cached token expires"""
        # This would require waiting 60 minutes or manipulating the cache
        # Skip for now - covered by manual testing
        pytest.skip("Requires 60+ minute wait or cache manipulation")
```

---

### 2. Unit Tests (Minimal - 10% of testing effort)

**File**: `azure-function/tests/test_unit.py`

```python
import pytest
from datetime import datetime, timedelta
from GetGUID import get_cached_token, cache_token, _token_cache

class TestTokenCachingLogic:
    """Test pure token caching logic (no AWS calls)"""

    def setup_method(self):
        """Clear cache before each test"""
        _token_cache['access_token'] = None
        _token_cache['expires_at'] = None

    def test_get_cached_token_returns_none_when_empty(self):
        """Empty cache should return None"""
        assert get_cached_token() is None

    def test_cache_token_stores_with_expiration(self):
        """Caching should calculate correct expiration"""
        test_token = "test_token_123"
        expires_in = 3600  # 1 hour

        cache_token(test_token, expires_in)

        assert _token_cache['access_token'] == test_token
        assert _token_cache['expires_at'] is not None

        # Should expire in approximately 1 hour (within 5 seconds tolerance)
        expected_expiry = datetime.now() + timedelta(seconds=expires_in)
        actual_expiry = _token_cache['expires_at']

        time_diff = abs((expected_expiry - actual_expiry).total_seconds())
        assert time_diff < 5  # Within 5 seconds

    def test_get_cached_token_returns_valid_token(self):
        """Valid cached token should be returned"""
        test_token = "valid_token_456"
        cache_token(test_token, 3600)

        retrieved = get_cached_token()
        assert retrieved == test_token

    def test_get_cached_token_returns_none_when_expired(self):
        """Expired token should not be returned"""
        test_token = "expired_token"

        # Cache with expiration in the past
        _token_cache['access_token'] = test_token
        _token_cache['expires_at'] = datetime.now() - timedelta(seconds=10)

        assert get_cached_token() is None

    def test_cache_includes_60_second_buffer(self):
        """Token should be considered expired 60s before actual expiry"""
        test_token = "buffer_test_token"

        # Set expiration to 50 seconds from now (within buffer)
        _token_cache['access_token'] = test_token
        _token_cache['expires_at'] = datetime.now() + timedelta(seconds=50)

        # Should return None because within 60s buffer
        assert get_cached_token() is None

    def test_cache_token_overwrites_existing(self):
        """New token should overwrite old cached token"""
        cache_token("old_token", 3600)
        cache_token("new_token", 3600)

        assert get_cached_token() == "new_token"
```

---

### 3. Manual Testing Checklist

**Power Platform Custom Connector Tests**:

- [ ] **Direct Connector** (`jr_getnino`)
  - [ ] Create connection with Function key
  - [ ] Test with valid GUID
  - [ ] Test with invalid GUID
  - [ ] Verify response time (<500ms warm)
  - [ ] Test error scenarios

- [ ] **APIM Connector** (`new_5Fguid-20service-20api`)
  - [ ] Create connection with APIM subscription key
  - [ ] Test with valid GUID
  - [ ] Test APIM caching (second call <50ms)
  - [ ] Test rate limiting (>1000 calls/hour)
  - [ ] Verify APIM analytics working

- [ ] **Power Automate Flow**
  - [ ] Build test flow with both connectors
  - [ ] Verify outputs match expected format
  - [ ] Test error handling in flow

---

## Test Environment Setup

### Local Development

```bash
# Install dependencies
cd azure-function
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov

# Set environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="eu-west-2"
export AWS_SECRET_NAME="consumer/cognito/vpn-lab/credentials"
export COGNITO_DOMAIN="vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com"
export GUID_API_URL="https://z3euh2qc03.execute-api.eu-west-2.amazonaws.com/test"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=GetGUID --cov-report=html
```

### CI/CD Pipeline

**GitHub Actions**: `.github/workflows/test.yml`

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd azure-function
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run integration tests
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: eu-west-2
          AWS_SECRET_NAME: consumer/cognito/vpn-lab/credentials
          COGNITO_DOMAIN: ${{ secrets.COGNITO_DOMAIN }}
          GUID_API_URL: ${{ secrets.GUID_API_URL }}
        run: |
          cd azure-function
          pytest tests/test_integration.py -v

      - name: Run unit tests
        run: |
          cd azure-function
          pytest tests/test_unit.py -v --cov=GetGUID

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Test Data

### Test GUID
```
123e4567-e89b-12d3-a456-426614174000
```

### Expected Response
```json
{
  "guid": "123e4567-e89b-12d3-a456-426614174000",
  "nino": "AB123456C",
  "firstName": "John",
  "lastName": "Doe",
  "dateOfBirth": "1990-01-01",
  "source": "Mock NINO Service",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

---

## Acceptance Criteria

### Integration Tests
- ✅ All integration tests pass with real AWS services
- ✅ End-to-end flow completes successfully
- ✅ Token caching verified to work
- ✅ Error scenarios handled correctly

### Unit Tests
- ✅ Token caching logic tests pass
- ✅ Edge cases covered (expiration, buffer, etc.)

### Manual Tests
- ✅ Both Custom Connectors work in Power Platform
- ✅ Power Automate flow successfully retrieves NINO
- ✅ Error handling works as expected

### Performance
- ✅ Cold start < 3 seconds
- ✅ Warm response < 500ms (direct)
- ✅ APIM cache hit < 50ms
- ✅ Token cache reduces Cognito calls by 95%+

---

## Why This Approach Works

**Confidence**: Tests prove actual AWS integration works
**Simplicity**: Less code, easier to maintain
**Speed**: No mock setup complexity
**Reality**: Catches real API changes, credential issues
**Handover**: Client can run same tests in their environment

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Just integration
pytest tests/test_integration.py -v

# Just unit
pytest tests/test_unit.py -v

# With coverage
pytest tests/ -v --cov=GetGUID --cov-report=html

# Specific test
pytest tests/test_integration.py::TestRealAWSIntegration::test_end_to_end_flow -v
```

---

**Status**: Ready for implementation
**Next**: Create test files and requirements-dev.txt
