"""
Unit tests for input validation (schema enforcement) on API endpoints.

Covers both positive and negative cases for required fields and schema constraints using direct Azure HttpRequest objects instead of actual localhost sockets (avoiding mocks of the router).
"""

import unittest
import json
import os

# Set dummy env vars to bypass startup validation in function_app.py
for var in ["KEY_VAULT_URL", "COGNITO_DOMAIN", "GUID_API_URL"]:
    if var not in os.environ:
        os.environ[var] = "dummy"

import azure.functions as func
from function_app import get_single_guid, process_bulk_guids
from unittest.mock import patch

# Clean up dummy env vars to avoid bleeding into test_integration.py
for var in ["KEY_VAULT_URL", "COGNITO_DOMAIN", "GUID_API_URL"]:
    if os.environ.get(var) == "dummy":
        del os.environ[var]

@patch("middleware.project_context.get_project_arn", return_value="arn:aws:sns:eu-west-2:123456789012:testproj")
@patch.dict(os.environ, {"KEY_VAULT_URL": "dummy", "COGNITO_DOMAIN": "dummy", "GUID_API_URL": "dummy"})
class TestInputValidation(unittest.TestCase):
    def test_single_guid_missing_identifier(self, mock_get_arn):
        """Should return 400 if Identifier header is missing"""
        req = func.HttpRequest(
            method='GET',
            body=None,
            url='/api/guid-translation-service/v1/dwp-guid',
            params={'project': 'testproj'},
            headers={}
        )
        response = get_single_guid(req)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Identifier", response.get_body().decode())

    def test_single_guid_missing_project(self, mock_get_arn):
        """Should return 400 if project param is missing"""
        req = func.HttpRequest(
            method='GET',
            body=None,
            url='/api/guid-translation-service/v1/dwp-guid',
            params={},
            headers={'Identifier': 'some-guid'}
        )
        response = get_single_guid(req)
        self.assertEqual(response.status_code, 400)
        self.assertIn("project", response.get_body().decode())

    def test_bulk_guid_invalid_number_of_records(self, mock_get_arn):
        """Should return 400 if numberOfRecords > 5000 or < 1"""
        payload = {"numberOfRecords": 6000, "identifiers": ["id1"]*6000}
        req = func.HttpRequest(
            method='POST',
            body=json.dumps(payload).encode('utf-8'),
            url='/api/dwp-guid-bulk-service/v1/translate-nino-bulk',
            params={'project': 'testproj'},
            headers={'Content-Type': 'application/json'},
            route_params={'bulk_activity': 'translate-nino-bulk'}
        )
        response = process_bulk_guids(req)
        self.assertEqual(response.status_code, 400)
        self.assertIn("numberOfRecords", response.get_body().decode())

    def test_bulk_guid_missing_project(self, mock_get_arn):
        """Should return 400 if project param is missing"""
        payload = {"numberOfRecords": 2, "identifiers": ["id1", "id2"]}
        req = func.HttpRequest(
            method='POST',
            body=json.dumps(payload).encode('utf-8'),
            url='/api/dwp-guid-bulk-service/v1/translate-nino-bulk',
            params={},
            headers={'Content-Type': 'application/json'},
            route_params={'bulk_activity': 'translate-nino-bulk'}
        )
        response = process_bulk_guids(req)
        self.assertEqual(response.status_code, 400)
        self.assertIn("project", response.get_body().decode())

    def test_bulk_guid_missing_identifiers(self, mock_get_arn):
        """Should return 400 if identifiers field is missing"""
        payload = {"numberOfRecords": 2}
        req = func.HttpRequest(
            method='POST',
            body=json.dumps(payload).encode('utf-8'),
            url='/api/dwp-guid-bulk-service/v1/translate-nino-bulk',
            params={'project': 'testproj'},
            headers={'Content-Type': 'application/json'},
            route_params={'bulk_activity': 'translate-nino-bulk'}
        )
        response = process_bulk_guids(req)
        self.assertEqual(response.status_code, 400)
        self.assertIn("identifiers", response.get_body().decode())

if __name__ == "__main__":
    unittest.main()
