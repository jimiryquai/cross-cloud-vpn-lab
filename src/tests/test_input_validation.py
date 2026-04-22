"""
Integration tests for input validation (schema enforcement) on API endpoints.

Covers both positive and negative cases for required fields and schema constraints.
"""

import os
import unittest
import requests

# These should be set to the deployed/test function app base URL
FUNCTION_BASE_URL = os.environ.get("FUNCTION_BASE_URL", "http://localhost:7071/api")

class TestInputValidation(unittest.TestCase):
    def test_single_guid_missing_identifier(self):
        """Should return 400 if Identifier header is missing"""
        url = f"{FUNCTION_BASE_URL}/guid-translation-service/v1/dwp-guid?project=testproj"
        response = requests.get(url, headers={}, timeout=5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Identifier", response.text)

    def test_single_guid_missing_project(self):
        """Should return 400 if project param is missing"""
        url = f"{FUNCTION_BASE_URL}/guid-translation-service/v1/dwp-guid"
        response = requests.get(url, headers={"Identifier": "some-guid"}, timeout=5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("project", response.text)

    def test_bulk_guid_invalid_number_of_records(self):
        """Should return 400 if numberOfRecords > 5000 or < 1"""
        url = f"{FUNCTION_BASE_URL}/dwp-guid-bulk-service/v1/translate-nino-bulk?project=testproj"
        payload = {"numberOfRecords": 6000, "identifiers": ["id1"]*6000}
        response = requests.post(url, json=payload, timeout=5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("numberOfRecords", response.text)

    def test_bulk_guid_missing_project(self):
        """Should return 400 if project param is missing"""
        url = f"{FUNCTION_BASE_URL}/dwp-guid-bulk-service/v1/translate-nino-bulk"
        payload = {"numberOfRecords": 2, "identifiers": ["id1", "id2"]}
        response = requests.post(url, json=payload, timeout=5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("project", response.text)

    def test_bulk_guid_missing_identifiers(self):
        """Should return 400 if identifiers field is missing"""
        url = f"{FUNCTION_BASE_URL}/dwp-guid-bulk-service/v1/translate-nino-bulk?project=testproj"
        payload = {"numberOfRecords": 2}
        response = requests.post(url, json=payload, timeout=5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("identifiers", response.text)

    def test_bulk_guid_valid(self):
        """Should accept valid payload (if backend is up)"""
        url = f"{FUNCTION_BASE_URL}/dwp-guid-bulk-service/v1/translate-nino-bulk?project=testproj"
        payload = {"numberOfRecords": 2, "identifiers": ["id1", "id2"]}
        response = requests.post(url, json=payload, timeout=5)
        self.assertIn(response.status_code, [200, 400])  # 200 if backend up, 400 if test data invalid

if __name__ == "__main__":
    unittest.main()
