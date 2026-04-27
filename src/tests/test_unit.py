"""
Unit tests for pure logic (no external dependencies).

Tests token caching and secrets caching logic — no Azure Key Vault
or AWS calls. Just datetime calculations and dict operations.
"""

from datetime import datetime, timedelta
import unittest

from shared.auth.token import get_cached_token, cache_token, _token_cache

# Secret caching logic
from shared.auth.secret import get_cognito_credentials, _secrets_cache
import os
import logging
import types

# Test-only tokens (not for production)
TEST_TOKEN_1 = "test_token_123"
TEST_TOKEN_2 = "valid_token_456"
TEST_TOKEN_3 = "expired_token"
TEST_TOKEN_4 = "buffer_test_token"
TEST_TOKEN_5 = "old_token"
TEST_TOKEN_6 = "new_token"


class TestTokenCachingLogic(unittest.TestCase):
    """Test pure token caching logic (no AWS calls)"""

    def setUp(self):
        _token_cache["access_token"] = None
        _token_cache["expires_at"] = None

    def tearDown(self):
        _token_cache["access_token"] = None
        _token_cache["expires_at"] = None

    def test_get_cached_token_returns_none_when_empty(self):
        result = get_cached_token()
        self.assertIsNone(result, "Empty cache should return None")

    def test_cache_token_stores_with_expiration(self):
        expires_in = 3600  # 1 hour
        cache_token(TEST_TOKEN_1, expires_in)
        self.assertEqual(_token_cache["access_token"], TEST_TOKEN_1)
        self.assertIsNotNone(_token_cache["expires_at"])
        expected_expiry = datetime.now() + timedelta(seconds=expires_in)
        actual_expiry = _token_cache["expires_at"]
        time_diff = abs((expected_expiry - actual_expiry).total_seconds())
        self.assertLess(time_diff, 5, f"Expiration should be ~1 hour from now (diff: {time_diff}s)")

    def test_get_cached_token_returns_valid_token(self):
        cache_token(TEST_TOKEN_2, 3600)
        retrieved = get_cached_token()
        self.assertEqual(retrieved, TEST_TOKEN_2)

    def test_get_cached_token_returns_none_when_expired(self):
        _token_cache["access_token"] = TEST_TOKEN_3
        _token_cache["expires_at"] = datetime.now() - timedelta(seconds=10)
        result = get_cached_token()
        self.assertIsNone(result, "Expired token should not be returned")

    def test_cache_includes_60_second_buffer(self):
        _token_cache["access_token"] = TEST_TOKEN_4
        _token_cache["expires_at"] = datetime.now() + timedelta(seconds=50)
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
            ("short_token", 60),  # 1 minute
            ("medium_token", 1800),  # 30 minutes
            ("long_token", 3600),  # 1 hour
        ]
        for token, expires_in in test_cases:
            cache_token(token, expires_in)
            expected_expiry = datetime.now() + timedelta(seconds=expires_in)
            actual_expiry = _token_cache["expires_at"]
            time_diff = abs((expected_expiry - actual_expiry).total_seconds())
            self.assertLess(time_diff, 5, f"Expiration calculation should be accurate for {expires_in}s")


if __name__ == "__main__":
    unittest.main()


class TestSecretCachingLogic(unittest.TestCase):
    """Test pure secret caching logic (no Azure Key Vault calls)"""

    def setUp(self):
        _secrets_cache["client_id"] = None
        _secrets_cache["client_secret"] = None

    def tearDown(self):
        _secrets_cache["client_id"] = None
        _secrets_cache["client_secret"] = None

    def test_cache_hit_returns_cached_secrets(self):
        _secrets_cache["client_id"] = "cached_id"
        _secrets_cache["client_secret"] = "cached_secret"
        client_id, client_secret = get_cognito_credentials(secret_client="dummy")
        self.assertEqual(client_id, "cached_id")
        self.assertEqual(client_secret, "cached_secret")

    def test_cache_miss_fetches_and_caches(self):
        class DummySecret:
            def __init__(self, value):
                self.value = value

        class DummyClient:
            def get_secret(self, name):
                return DummySecret(f"{name}_value")

        orig_environ = os.environ.copy()
        os.environ["KEY_VAULT_URL"] = "dummy-url"
        try:
            _secrets_cache["client_id"] = None
            _secrets_cache["client_secret"] = None
            client_id, client_secret = get_cognito_credentials(secret_client=DummyClient())
            self.assertEqual(client_id, "cognito-client-id_value")
            self.assertEqual(client_secret, "cognito-client-secret_value")
            # Should be cached now
            self.assertEqual(_secrets_cache["client_id"], "cognito-client-id_value")
            self.assertEqual(_secrets_cache["client_secret"], "cognito-client-secret_value")
        finally:
            os.environ.clear()
            os.environ.update(orig_environ)

    def test_error_on_missing_key_vault_url(self):
        # Patch os.environ to not have KEY_VAULT_URL
        orig_environ = os.environ.copy()
        os.environ.pop("KEY_VAULT_URL", None)
        _secrets_cache["client_id"] = None
        _secrets_cache["client_secret"] = None
        with self.assertRaises(Exception) as ctx:
            get_cognito_credentials(secret_client=types.SimpleNamespace(get_secret=lambda n: None))
        self.assertIn("KEY_VAULT_URL", str(ctx.exception))
        os.environ.clear()
        os.environ.update(orig_environ)

    def test_logging_on_error(self):
        # Patch os.environ to not have KEY_VAULT_URL
        orig_environ = os.environ.copy()
        os.environ.pop("KEY_VAULT_URL", None)
        _secrets_cache["client_id"] = None
        _secrets_cache["client_secret"] = None
        logs = []

        def fake_log(msg):
            logs.append(msg)

        orig_log = logging.error
        logging.error = fake_log
        try:
            with self.assertRaises(Exception):
                get_cognito_credentials(secret_client=types.SimpleNamespace(get_secret=lambda n: None))
        finally:
            logging.error = orig_log
            os.environ.clear()
            os.environ.update(orig_environ)
        self.assertTrue(any("Error retrieving credentials" in l for l in logs))

    def test_parameterized_secret_names(self):
        class DummySecret:
            def __init__(self, value):
                self.value = value

        class DummyClient:
            def get_secret(self, name):
                return DummySecret(f"{name}_value")

        orig_environ = os.environ.copy()
        os.environ["KEY_VAULT_URL"] = "dummy-url"
        os.environ["COGNITO_CLIENT_ID_SECRET_NAME"] = "custom-client-id"
        os.environ["COGNITO_CLIENT_SECRET_SECRET_NAME"] = "custom-client-secret"
        _secrets_cache["client_id"] = None
        _secrets_cache["client_secret"] = None
        client_id, client_secret = get_cognito_credentials(secret_client=DummyClient())
        self.assertEqual(client_id, "custom-client-id_value")
        self.assertEqual(client_secret, "custom-client-secret_value")
        os.environ.clear()
        os.environ.update(orig_environ)
