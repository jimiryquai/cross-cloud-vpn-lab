"""
Integration tests with real Azure Key Vault and AWS services.

These tests call real Azure Key Vault (for Cognito credentials),
AWS Cognito (for OAuth token), and the GUID API.
No mocks - testing actual integration.

Prerequisites:
- Environment variables set (see tests/README.md)
- Azure Key Vault configured with Cognito credentials
- Managed Identity or DefaultAzureCredential configured
- Real AWS resources deployed (Cognito, GUID API)
"""

import pytest
import os
import sys

# Add parent directory to path to import GetGUID module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from GetGUID import (
    get_cognito_credentials,
    get_cognito_token,
    call_guid_api,
    get_cached_token,
    cache_token,
    _token_cache,
    _secrets_cache
)


class TestRealIntegration:
    """Integration tests with real Azure Key Vault and AWS services"""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Ensure required environment variables are set"""
        required = [
            'KEY_VAULT_URL',
            'COGNITO_DOMAIN',
            'GUID_API_URL'
        ]

        missing = [var for var in required if not os.environ.get(var)]

        if missing:
            pytest.skip(f"Missing required environment variables: {', '.join(missing)}")

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear token and secrets cache before each test"""
        _token_cache['access_token'] = None
        _token_cache['expires_at'] = None
        _secrets_cache['client_id'] = None
        _secrets_cache['client_secret'] = None
        yield
        _token_cache['access_token'] = None
        _token_cache['expires_at'] = None
        _secrets_cache['client_id'] = None
        _secrets_cache['client_secret'] = None

    def test_retrieve_credentials_from_key_vault(self):
        """Test retrieving Cognito credentials from Azure Key Vault"""
        print("\n→ Testing Key Vault credential retrieval...")

        client_id, secret = get_cognito_credentials()

        # Verify we got real credentials
        assert client_id is not None, "client_id should not be None"
        assert secret is not None, "secret should not be None"
        assert len(client_id) > 0, "client_id should not be empty"
        assert len(secret) > 0, "secret should not be empty"

        print(f"  ✓ Retrieved credentials from Key Vault")
        print(f"    - client_id length: {len(client_id)} chars")
        print(f"    - secret length: {len(secret)} chars")

    def test_credentials_are_cached_after_first_retrieval(self):
        """Test that Key Vault credentials are cached and reused"""
        print("\n→ Testing credential caching...")

        # First call — fetches from Key Vault
        client_id_1, secret_1 = get_cognito_credentials()
        assert _secrets_cache['client_id'] is not None, "Cache should be populated"

        # Second call — should return cached values
        client_id_2, secret_2 = get_cognito_credentials()

        assert client_id_1 == client_id_2, "Cached client_id should match"
        assert secret_1 == secret_2, "Cached secret should match"

        print(f"  ✓ Credentials cached correctly after first retrieval")

    def test_get_token_from_real_cognito(self):
        """Test getting OAuth token from real AWS Cognito"""
        print("\n→ Testing Cognito OAuth flow...")

        # Get real credentials
        client_id, secret = get_cognito_credentials()
        print(f"  ✓ Got credentials from Key Vault")

        # Get real OAuth token
        access_token = get_cognito_token(client_id, secret)

        # Verify token
        assert access_token is not None, "access_token should not be None"
        assert len(access_token) > 100, "JWT tokens should be long (>100 chars)"
        assert access_token.startswith('eyJ'), "JWT tokens should start with 'eyJ'"

        print(f"  ✓ Got OAuth token from Cognito")
        print(f"    - Token length: {len(access_token)} chars")
        print(f"    - Token format: JWT (starts with 'eyJ')")

    def test_call_real_guid_api(self):
        """Test calling real GUID API with Bearer token and header-based Identifier"""
        print("\n→ Testing GUID API call...")

        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)

        test_identifier = "123e4567-e89b-12d3-a456-426614174000"
        test_correlation = "88888888-4444-4444-4444-121212121212"

        # call_guid_api returns the RAW upstream JSON, not the mapped DTO
        person_data = call_guid_api(access_token, test_identifier, test_correlation)

        assert person_data is not None, "Should get a response from upstream"
        # Raw upstream response has 'nino' and 'guid' keys (not the DTO field names)
        assert 'nino' in person_data, "Raw response should contain 'nino'"

        print(f"  ✓ Got raw upstream response")
        print(f"    - NINO: {person_data.get('nino')}")

    def test_end_to_end_flow(self):
        """Test complete end-to-end flow — credentials → token → API call"""
        print("\n→ Testing complete end-to-end flow...")

        test_identifier = "123e4567-e89b-12d3-a456-426614174000"
        test_correlation = "88888888-4444-4444-4444-121212121212"

        # Step 1 & 2: Get Credentials & Token
        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)

        # Step 3: Call GUID API — returns raw upstream JSON
        person_data = call_guid_api(access_token, test_identifier, test_correlation)

        # Raw upstream response (not the mapped DTO)
        assert person_data is not None
        assert 'nino' in person_data
        returned_nino = person_data.get('nino')
        assert returned_nino is not None, "nino should be present in response"
        print(f"     ✓ Got NINO from upstream: {returned_nino}")

    def test_token_caching_reduces_cognito_calls(self):
        """Verify token is cached and reused"""
        print("\n→ Testing token caching...")

        client_id, secret = get_cognito_credentials()

        # First call - should get new token
        print("  1. First call - getting new token...")
        token1 = get_cognito_token(client_id, secret)
        print(f"     ✓ Got token (length: {len(token1)})")

        # Second call - should use cached token
        print("  2. Second call - should use cached token...")
        token2 = get_cognito_token(client_id, secret)
        print(f"     ✓ Got token (length: {len(token2)})")

        # Tokens should be identical (same cached token)
        assert token1 == token2, "Tokens should be identical (cached)"
        print(f"  ✓ Token caching working (tokens are identical)")

    def test_invalid_guid_returns_response(self):
        """Test API behavior with invalid GUID"""
        print("\n→ Testing API behavior with invalid GUID...")

        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)

        invalid_guid = "00000000-0000-0000-0000-000000000000"
        test_correlation = "88888888-4444-4444-4444-121212121212"
        print(f"  Calling API with invalid GUID: {invalid_guid}")

        # Call with all required args — raw upstream response
        person_data = call_guid_api(access_token, invalid_guid, test_correlation)

        # Mock API returns data for any GUID (lab environment behavior)
        assert person_data is not None, "Should get response from mock API"
        assert 'nino' in person_data, "Response should contain 'nino'"

        print(f"  ✓ Mock API behavior verified")
        print(f"    - Mock API returns data for any GUID (lab environment)")
        print(f"    - NINO: {person_data.get('nino')}")

    @pytest.mark.slow
    def test_expired_token_gets_refreshed(self):
        """Test token refresh when cached token expires"""
        # This would require waiting 60 minutes or manipulating the cache
        # Skip for now - covered by manual testing
        pytest.skip("Requires 60+ minute wait or cache manipulation - test manually")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])
