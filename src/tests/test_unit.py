"""
Unit tests for pure logic (no external dependencies).

Tests token caching and secrets caching logic — no Azure Key Vault
or AWS calls. Just datetime calculations and dict operations.
"""


import os
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch, MagicMock

from shared.auth import get_cached_token, cache_token, _token_cache, _secrets_cache, get_cognito_credentials

# Test-only secrets/tokens (not for production)
TEST_TOKEN_1 = "test_token_123"
TEST_TOKEN_2 = "valid_token_456"
TEST_TOKEN_3 = "expired_token"
TEST_TOKEN_4 = "buffer_test_token"
TEST_TOKEN_5 = "old_token"
TEST_TOKEN_6 = "new_token"
TEST_CLIENT_ID = "cached-id"
TEST_CLIENT_SECRET = "cached-secret"
TEST_CLIENT_ID_2 = "test-client-id"
TEST_CLIENT_SECRET_2 = "test-client-secret"


class TestTokenCachingLogic(unittest.TestCase):
    """Test pure token caching logic (no AWS calls)"""

    def setUp(self):
        _token_cache['access_token'] = None
        _token_cache['expires_at'] = None

    def tearDown(self):
        _token_cache['access_token'] = None
        _token_cache['expires_at'] = None

    def test_get_cached_token_returns_none_when_empty(self):
        result = get_cached_token()
        self.assertIsNone(result, "Empty cache should return None")

    def test_cache_token_stores_with_expiration(self):
        expires_in = 3600  # 1 hour
        cache_token(TEST_TOKEN_1, expires_in)
        self.assertEqual(_token_cache['access_token'], TEST_TOKEN_1)
        self.assertIsNotNone(_token_cache['expires_at'])
        expected_expiry = datetime.now() + timedelta(seconds=expires_in)
        actual_expiry = _token_cache['expires_at']
        time_diff = abs((expected_expiry - actual_expiry).total_seconds())
        self.assertLess(time_diff, 5, f"Expiration should be ~1 hour from now (diff: {time_diff}s)")

    def test_get_cached_token_returns_valid_token(self):
        cache_token(TEST_TOKEN_2, 3600)
        retrieved = get_cached_token()
        self.assertEqual(retrieved, TEST_TOKEN_2)

    def test_get_cached_token_returns_none_when_expired(self):
        _token_cache['access_token'] = TEST_TOKEN_3
        _token_cache['expires_at'] = datetime.now() - timedelta(seconds=10)
        result = get_cached_token()
        self.assertIsNone(result, "Expired token should not be returned")

    def test_cache_includes_60_second_buffer(self):
        _token_cache['access_token'] = TEST_TOKEN_4
        _token_cache['expires_at'] = datetime.now() + timedelta(seconds=50)
        result = get_cached_token()
        self.assertIsNone(result, "Token within 60s buffer should not be returned")

    def test_cache_token_overwrites_existing(self):
        cache_token(TEST_TOKEN_5, 3600)
        old_token = get_cached_token()
        self.assertEqual(old_token, TEST_TOKEN_5)
        cache_token(TEST_TOKEN_6, 3600)
        new_token = get_cached_token()
        self.assertEqual(new_token, TEST_TOKEN_6)
        self.assertNotEqual(new_token, old_token)

    def test_cache_with_different_expiration_times(self):
        test_cases = [
            ("short_token", 60),      # 1 minute
            ("medium_token", 1800),   # 30 minutes
            ("long_token", 3600),     # 1 hour
        ]
        for token, expires_in in test_cases:
            cache_token(token, expires_in)
            expected_expiry = datetime.now() + timedelta(seconds=expires_in)
            actual_expiry = _token_cache['expires_at']
            time_diff = abs((expected_expiry - actual_expiry).total_seconds())
            self.assertLess(time_diff, 5, f"Expiration calculation should be accurate for {expires_in}s")



class TestSecretsCachingLogic(unittest.TestCase):
    """Test Key Vault secrets caching (mocked — no real Key Vault calls)"""

    def setUp(self):
        _secrets_cache['client_id'] = None
        _secrets_cache['client_secret'] = None

    def tearDown(self):
        _secrets_cache['client_id'] = None
        _secrets_cache['client_secret'] = None

    def test_secrets_cache_returns_cached_values(self):
        _secrets_cache['client_id'] = TEST_CLIENT_ID
        _secrets_cache['client_secret'] = TEST_CLIENT_SECRET
        client_id, client_secret = get_cognito_credentials()
        self.assertEqual(client_id, TEST_CLIENT_ID)
        self.assertEqual(client_secret, TEST_CLIENT_SECRET)

    def test_get_cognito_credentials_raises_without_key_vault_url(self):
        _secrets_cache['client_id'] = None
        _secrets_cache['client_secret'] = None
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(Exception) as cm:
                get_cognito_credentials()
            self.assertIn("KEY_VAULT_URL", str(cm.exception))

    @patch('shared.auth.SecretClient')
    @patch('shared.auth.DefaultAzureCredential')
    def test_get_cognito_credentials_fetches_and_caches(self, mock_cred, mock_client_cls):
        mock_secret_id = MagicMock()
        mock_secret_id.value = TEST_CLIENT_ID_2
        mock_secret_secret = MagicMock()
        mock_secret_secret.value = TEST_CLIENT_SECRET_2
        mock_client = MagicMock()
        mock_client.get_secret.side_effect = lambda name: {
            'cognito-client-id': mock_secret_id,
            'cognito-client-secret': mock_secret_secret,
        }[name]
        mock_client_cls.return_value = mock_client
        with patch.dict(os.environ, {'KEY_VAULT_URL': 'https://test-vault.vault.azure.net'}):
            client_id, client_secret = get_cognito_credentials()
        self.assertEqual(client_id, TEST_CLIENT_ID_2)
        self.assertEqual(client_secret, TEST_CLIENT_SECRET_2)
        self.assertEqual(_secrets_cache['client_id'], TEST_CLIENT_ID_2)
        self.assertEqual(_secrets_cache['client_secret'], TEST_CLIENT_SECRET_2)
        mock_client.get_secret.reset_mock()
        client_id_2, client_secret_2 = get_cognito_credentials()
        mock_client.get_secret.assert_not_called()
        self.assertEqual(client_id_2, TEST_CLIENT_ID_2)


if __name__ == "__main__":
    unittest.main()
