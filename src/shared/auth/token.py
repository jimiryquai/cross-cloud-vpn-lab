import os
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth

from typing import Dict, Any

_token_cache: Dict[str, Dict[str, Any]] = {}


def get_cached_token(project):
    """Return cached token if still valid (with 60s safety buffer)"""
    if project in _token_cache:
        tenant_cache = _token_cache[project]
        if datetime.now() < tenant_cache["expires_at"] - timedelta(seconds=60):
            return tenant_cache["access_token"]
    return None


def cache_token(project, access_token, expires_in):
    """Cache the token specifically under the project key"""
    _token_cache[project] = {"access_token": access_token, "expires_at": datetime.now() + timedelta(seconds=expires_in)}


def get_cognito_token(project, client_id, client_secret, requests_session=None):
    """Get OAuth token from Cognito (uses cache if valid)"""
    cached_token = get_cached_token(project)
    if cached_token:
        return cached_token

    cognito_domain = os.environ.get("COGNITO_DOMAIN")
    token_url = f"https://{cognito_domain}/oauth2/token"

    session = requests_session or requests
    response = session.post(
        token_url,
        auth=HTTPBasicAuth(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    # Ensure we don't cache empty garbage if the AWS request fails
    response.raise_for_status()

    token_data = response.json()
    cache_token(project, token_data["access_token"], token_data.get("expires_in", 3600))
    return token_data["access_token"]
