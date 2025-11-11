"""
Unit tests for pure logic (no external dependencies).

These tests focus on token caching logic that doesn't require AWS calls.
No mocks needed - just testing datetime calculations.
"""

import pytest
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to import GetGUID module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from GetGUID import get_cached_token, cache_token, _token_cache


class TestTokenCachingLogic:
    """Test pure token caching logic (no AWS calls)"""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test"""
        _token_cache['access_token'] = None
        _token_cache['expires_at'] = None
        yield
        _token_cache['access_token'] = None
        _token_cache['expires_at'] = None

    def test_get_cached_token_returns_none_when_empty(self):
        """Empty cache should return None"""
        print("\n→ Testing empty cache returns None...")

        result = get_cached_token()

        assert result is None, "Empty cache should return None"
        print("  ✓ Empty cache correctly returns None")

    def test_cache_token_stores_with_expiration(self):
        """Caching should calculate correct expiration"""
        print("\n→ Testing token storage with expiration...")

        test_token = "test_token_123"
        expires_in = 3600  # 1 hour

        cache_token(test_token, expires_in)

        assert _token_cache['access_token'] == test_token, "Token should be stored"
        assert _token_cache['expires_at'] is not None, "Expiration should be set"

        # Should expire in approximately 1 hour (within 5 seconds tolerance)
        expected_expiry = datetime.now() + timedelta(seconds=expires_in)
        actual_expiry = _token_cache['expires_at']

        time_diff = abs((expected_expiry - actual_expiry).total_seconds())
        assert time_diff < 5, f"Expiration should be ~1 hour from now (diff: {time_diff}s)"

        print(f"  ✓ Token stored with correct expiration")
        print(f"    - Token: {test_token}")
        print(f"    - Expires at: {actual_expiry}")
        print(f"    - Time diff from expected: {time_diff:.2f}s")

    def test_get_cached_token_returns_valid_token(self):
        """Valid cached token should be returned"""
        print("\n→ Testing retrieval of valid cached token...")

        test_token = "valid_token_456"
        cache_token(test_token, 3600)

        retrieved = get_cached_token()

        assert retrieved == test_token, "Should return cached token"
        print(f"  ✓ Retrieved valid cached token: {test_token}")

    def test_get_cached_token_returns_none_when_expired(self):
        """Expired token should not be returned"""
        print("\n→ Testing expired token returns None...")

        test_token = "expired_token"

        # Cache with expiration in the past
        _token_cache['access_token'] = test_token
        _token_cache['expires_at'] = datetime.now() - timedelta(seconds=10)

        result = get_cached_token()

        assert result is None, "Expired token should not be returned"
        print("  ✓ Expired token correctly returns None")

    def test_cache_includes_60_second_buffer(self):
        """Token should be considered expired 60s before actual expiry"""
        print("\n→ Testing 60-second expiration buffer...")

        test_token = "buffer_test_token"

        # Set expiration to 50 seconds from now (within 60s buffer)
        _token_cache['access_token'] = test_token
        _token_cache['expires_at'] = datetime.now() + timedelta(seconds=50)

        result = get_cached_token()

        # Should return None because within 60s buffer
        assert result is None, "Token within 60s buffer should not be returned"
        print("  ✓ 60-second buffer working correctly")
        print("    - Token expires in 50s")
        print("    - Correctly treated as expired due to 60s buffer")

    def test_cache_token_overwrites_existing(self):
        """New token should overwrite old cached token"""
        print("\n→ Testing token overwrite...")

        cache_token("old_token", 3600)
        old_token = get_cached_token()
        assert old_token == "old_token"
        print("  - Cached old_token")

        cache_token("new_token", 3600)
        new_token = get_cached_token()

        assert new_token == "new_token", "New token should overwrite old"
        assert new_token != old_token, "Should not return old token"
        print("  ✓ New token correctly overwrites old token")

    def test_cache_with_different_expiration_times(self):
        """Test caching with various expiration durations"""
        print("\n→ Testing various expiration durations...")

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

            assert time_diff < 5, f"Expiration calculation should be accurate for {expires_in}s"
            print(f"  ✓ Correct expiration for {expires_in}s ({expires_in//60} min)")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])
