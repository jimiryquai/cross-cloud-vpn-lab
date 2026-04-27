"""
Unit tests for environment variable validation logic in function_app.py
"""

import os
import unittest
from importlib import reload
import sys


class TestEnvVarValidation(unittest.TestCase):
    def setUp(self):
        # Backup and clear relevant env vars
        self._orig_env = os.environ.copy()
        for var in ["KEY_VAULT_URL", "COGNITO_DOMAIN", "GUID_API_URL"]:
            os.environ.pop(var, None)
        # Remove function_app from sys.modules to force reload
        sys.modules.pop("function_app", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)
        sys.modules.pop("function_app", None)

    def test_missing_env_vars_raises(self):
        # None set
        with self.assertRaises(RuntimeError) as ctx:
            import function_app

            reload(function_app)
        self.assertIn("Missing required environment variables", str(ctx.exception))

    def test_partial_env_vars_raises(self):
        os.environ["KEY_VAULT_URL"] = "dummy"
        with self.assertRaises(RuntimeError) as ctx:
            import function_app

            reload(function_app)
        self.assertIn("Missing required environment variables", str(ctx.exception))

    def test_all_env_vars_pass(self):
        os.environ["KEY_VAULT_URL"] = "dummy"
        os.environ["COGNITO_DOMAIN"] = "dummy"
        os.environ["GUID_API_URL"] = "dummy"
        try:
            import function_app

            reload(function_app)
        except RuntimeError:
            self.fail("validate_env_vars() raised unexpectedly when all vars set")


if __name__ == "__main__":
    unittest.main()
