# Test Strategy - Real Integration Testing

Focus on integration tests with real Azure and AWS services. Minimal unit tests only for pure logic.

---

## Philosophy

**Integration Over Mocks**: The Azure Function's purpose is orchestrating cross-cloud services. Test the real integration, not mocks.

**Test What Matters**:
- ✅ Does it work with real Azure Key Vault?
- ✅ Does it work with real AWS Cognito?
- ✅ Does it work with the real GUID API?
- ✅ Does token caching logic work correctly?
- ✅ Does input validation correctly filter invalid bulk inputs directly via `azure.functions.HttpRequest`?

**Skip What Doesn't**:
- ❌ Mocking AWS SDK or Azure Identity calls
- ❌ Mocking HTTP requests
- ❌ Testing that mocks were called correctly

---

## Test Structure

### 1. Integration Tests (Primary - 90% of testing effort)

**File**: `src/tests/test_integration.py`

```python
import unittest
import os
import json
from shared.auth.secret import get_cognito_credentials
from shared.auth.token import get_cognito_token
from function_app import call_guid_api

class TestRealIntegration(unittest.TestCase):
    """Integration tests with real cross-cloud services"""

    def setUp(self):
        """Ensure specific environment variables are set"""
        required = [
            'KEY_VAULT_URL',
            'COGNITO_DOMAIN',
            'GUID_API_URL'
        ]
        missing = [var for var in required if not os.environ.get(var)]
        if missing:
            self.skipTest(f"Missing required environment variables: {', '.join(missing)}")

    def test_retrieve_credentials_from_key_vault(self):
        """Test retrieving Cognito credentials from real Azure Key Vault"""
        client_id, secret = get_cognito_credentials("testproj")

        # Verify we got real credentials
        self.assertIsNotNone(client_id)
        self.assertIsNotNone(secret)
        self.assertGreater(len(client_id), 0)
        self.assertGreater(len(secret), 0)
        print(f"✓ Retrieved credentials from Azure Key Vault")

    def test_get_token_from_real_cognito(self):
        """Test getting OAuth token from real AWS Cognito"""
        # Get real credentials
        client_id, secret = get_cognito_credentials("testproj")

        # Get real OAuth token
        access_token = get_cognito_token(client_id, secret, "vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com")

        # Verify token
        self.assertIsNotNone(access_token)
        self.assertGreater(len(access_token), 100)  # JWT tokens are long
        self.assertTrue(access_token.startswith('eyJ'))  # JWT format
        print(f"✓ Got OAuth token from Cognito")

    def test_call_real_guid_api(self):
        """Test calling real GUID API with Bearer token"""
        # Get real credentials and token
        client_id, secret = get_cognito_credentials("testproj")
        access_token = get_cognito_token(client_id, secret, "vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com")

        # Call real API
        test_guid = "123e4567-e89b-12d3-a456-426614174000"
        person_data = call_guid_api(test_guid, access_token)

        # Verify response
        self.assertIsNotNone(person_data)
        self.assertIn('nino', person_data)
        self.assertIn('guid', person_data)
        self.assertEqual(person_data['guid'], test_guid)
        print(f"✓ Retrieved person data from GUID API: NINO={person_data['nino']}")

    def test_end_to_end_flow(self):
        """Test complete end-to-end flow with all real services"""
        test_guid = "123e4567-e89b-12d3-a456-426614174000"

        # Step 1: Get credentials from Azure Key Vault
        client_id, secret = get_cognito_credentials("testproj")
        self.assertTrue(client_id and secret)

        # Step 2: Get OAuth token from Cognito
        access_token = get_cognito_token(client_id, secret, "vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com")
        self.assertTrue(access_token)

        # Step 3: Call GUID API
        person_data = call_guid_api(test_guid, access_token)
        self.assertEqual(person_data['nino'], 'AB123456C')

        print(f"✓ Complete end-to-end flow successful")

    def test_token_caching_reduces_cognito_calls(self):
        """Verify token is cached and reused"""
        client_id, secret = get_cognito_credentials("testproj")

        # First call - should get new token
        token1 = get_cognito_token(client_id, secret, "vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com")

        # Second call - should use cached token (check logs)
        token2 = get_cognito_token(client_id, secret, "vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com")

        # Tokens should be identical (same cached token)
        self.assertEqual(token1, token2)
        print(f"✓ Token caching working (reused token)")

    def test_expired_token_gets_refreshed(self):
        """Test token refresh when cached token expires"""
        # This would require waiting 60 minutes or manipulating the cache
        # Skip for now - covered by manual testing
        self.skipTest("Requires 60+ minute wait or cache manipulation")
```

---

### 2. Unit Tests (Minimal - 10% of testing effort)

**File**: `src/tests/test_unit.py`

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

- [ ] **Direct Connector**
  - [ ] Create connection
  - [ ] Test with valid GUID
  - [ ] Test with invalid GUID
  - [ ] Verify response time (<500ms warm)
  - [ ] Test error scenarios

- [ ] **Power Automate Flow**
  - [ ] Build test flow
  - [ ] Verify outputs match expected format
  - [ ] Test error handling in flow

---

## Test Environment Setup

### Local Development

```bash
# Install dependencies
cd src
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export KEY_VAULT_URL="https://your-key-vault.vault.azure.net/"
export COGNITO_DOMAIN="vpn-lab-1762372102.auth.eu-west-2.amazoncognito.com"
export GUID_API_URL="https://z3euh2qc03.execute-api.eu-west-2.amazonaws.com/test"

# Note: Before running integration tests, make sure you are authenticated with Azure via Azure CLI 
# (az login) because the application uses DefaultAzureCredential.

# Run tests using python's built-in unittest
.venv/bin/coverage run -m unittest discover -s tests -v
.venv/bin/coverage report -m
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
          cd src
          pip install -r requirements.txt

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Run tests
        env:
          KEY_VAULT_URL: ${{ secrets.KEY_VAULT_URL }}
          COGNITO_DOMAIN: ${{ secrets.COGNITO_DOMAIN }}
          GUID_API_URL: ${{ secrets.GUID_API_URL }}
        run: |
          cd src
          coverage run -m unittest discover -s tests -v
          coverage xml
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
- ✅ All integration tests pass with real Azure/AWS services
- ✅ End-to-end flow completes successfully
- ✅ Token caching verified to work
- ✅ Error scenarios handled correctly
- ✅ Proper isolation from startup validations using `func.HttpRequest` tests

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

**Confidence**: Tests prove actual cloud integration works
**Simplicity**: Less code, easier to maintain
**Speed**: Tests hit locally generated memory-resident HTTP requests rather than orchestrant mocks
**Reality**: Catches real API changes, credential issues, validation failures before deployments
**Handover**: Client can run same tests in their environment

---

## Running Tests

```bash
# All tests
python -m unittest discover -s tests -v

# Just integration
python -m unittest tests.test_integration -v

# Just unit
python -m unittest tests.test_unit -v

# With coverage
coverage run -m unittest discover -s tests -v
coverage report -m
```

---

**Status**: Ready for implementation
**Next**: Create test files and requirements-dev.txt
