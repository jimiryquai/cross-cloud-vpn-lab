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

import os
import unittest
import requests
from shared.auth.secret import get_cognito_credentials, _secrets_cache
from shared.auth.token import get_cognito_token, _token_cache
from function_app import call_guid_api

# Test-only secrets/tokens (not for production)
TEST_IDENTIFIER = "123e4567-e89b-12d3-a456-426614174000"
TEST_CORRELATION = "88888888-4444-4444-4444-121212121212"
INVALID_GUID = "00000000-0000-0000-0000-000000000000"


class TestRealIntegration(unittest.TestCase):
    """Integration tests with real Azure Key Vault and AWS services"""

    def setUp(self):
        required = ["KEY_VAULT_URL", "COGNITO_DOMAIN", "GUID_API_URL"]
        missing = [var for var in required if not os.environ.get(var)]
        if missing:
            self.skipTest(f"Missing required environment variables: {', '.join(missing)}")
        _token_cache["access_token"] = None
        _token_cache["expires_at"] = None
        _secrets_cache["client_id"] = None
        _secrets_cache["client_secret"] = None

    def tearDown(self):
        _token_cache["access_token"] = None
        _token_cache["expires_at"] = None
        _secrets_cache["client_id"] = None
        _secrets_cache["client_secret"] = None

    def test_retrieve_credentials_from_key_vault(self):
        client_id, secret = get_cognito_credentials()
        self.assertIsNotNone(client_id, "client_id should not be None")
        self.assertIsNotNone(secret, "secret should not be None")
        self.assertGreater(len(client_id), 0, "client_id should not be empty")
        self.assertGreater(len(secret), 0, "secret should not be empty")

    def test_credentials_are_cached_after_first_retrieval(self):
        client_id_1, secret_1 = get_cognito_credentials()
        self.assertIsNotNone(_secrets_cache["client_id"], "Cache should be populated")
        client_id_2, secret_2 = get_cognito_credentials()
        self.assertEqual(client_id_1, client_id_2, "Cached client_id should match")
        self.assertEqual(secret_1, secret_2, "Cached secret should match")

    def test_get_token_from_real_cognito(self):
        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)
        self.assertIsNotNone(access_token, "access_token should not be None")
        self.assertGreater(len(access_token), 100, "JWT tokens should be long (>100 chars)")
        self.assertTrue(access_token.startswith("eyJ"), "JWT tokens should start with 'eyJ'")

    def test_call_real_guid_api(self):
        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)
        person_data = call_guid_api(access_token, TEST_IDENTIFIER, TEST_CORRELATION)
        self.assertIsNotNone(person_data, "Should get a response from upstream")
        self.assertIn("nino", person_data, "Raw response should contain 'nino'")

    def test_end_to_end_flow(self):
        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)
        person_data = call_guid_api(access_token, TEST_IDENTIFIER, TEST_CORRELATION)
        self.assertIsNotNone(person_data)
        self.assertIn("nino", person_data)
        returned_nino = person_data.get("nino")
        self.assertIsNotNone(returned_nino, "nino should be present in response")

    def test_token_caching_reduces_cognito_calls(self):
        client_id, secret = get_cognito_credentials()
        token1 = get_cognito_token(client_id, secret)
        token2 = get_cognito_token(client_id, secret)
        self.assertEqual(token1, token2, "Tokens should be identical (cached)")

    def test_invalid_guid_returns_response(self):
        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)
        person_data = call_guid_api(access_token, INVALID_GUID, TEST_CORRELATION)
        self.assertIsNotNone(person_data, "Should get response from mock API")
        self.assertIn("nino", person_data, "Response should contain 'nino'")

    def test_bulk_endpoint_real(self):
        """Integration test for the bulk endpoint."""
        required = ["KEY_VAULT_URL", "COGNITO_DOMAIN", "GUID_API_URL", "FUNCTION_BASE_URL"]
        missing = [var for var in required if not os.environ.get(var)]
        if missing:
            self.skipTest(f"Missing required environment variables: {', '.join(missing)}")
        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)
        correlation_id = TEST_CORRELATION
        bulk_activity = "translate-nino-bulk"
        url = f"{os.environ['FUNCTION_BASE_URL']}/dwp-guid-bulk-service/v1/{bulk_activity}"
        payload = {"numberOfRecords": 2, "records": ["NINO1", "NINO2"]}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "correlation-id": correlation_id,
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        self.assertIn(response.status_code, [200, 400], "Should return 200 OK or 400 BAD_REQUEST for test payload")

    def test_daily_allowance_endpoint_real(self):
        """Integration test for the daily allowance endpoint."""
        required = ["KEY_VAULT_URL", "COGNITO_DOMAIN", "GUID_API_URL", "FUNCTION_BASE_URL"]
        missing = [var for var in required if not os.environ.get(var)]
        if missing:
            self.skipTest(f"Missing required environment variables: {', '.join(missing)}")
        client_id, secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, secret)
        correlation_id = TEST_CORRELATION
        url = f"{os.environ['FUNCTION_BASE_URL']}/dwp-guid-bulk-service/v1/remaining-daily-allowance"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "correlation-id": correlation_id,
        }
        response = requests.get(url, headers=headers, timeout=10)
        self.assertEqual(response.status_code, 200, "Should return 200 OK for daily allowance endpoint")

    @unittest.skip("Requires 60+ minute wait or cache manipulation - test manually")
    def test_expired_token_gets_refreshed(self):
        pass


if __name__ == "__main__":
    unittest.main()
