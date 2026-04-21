def get_project_arn(project):
    """
    Fetch the ACM Certificate ARN for the given project from Azure Key Vault.
    Allowed projects: FQM, 1ACS, HousingBenefit, MATB1
    """
    allowed_projects = {"FQM", "1ACS", "HousingBenefit", "MATB1"}
    if project not in allowed_projects:
        raise ValueError(f"Invalid project: {project}. Must be one of: {', '.join(allowed_projects)}")

    # Construct secret name (e.g., fqm-acm-arn)
    secret_name = f"{project.lower()}-acm-arn"

    key_vault_url = os.environ.get('KEY_VAULT_URL')
    if not key_vault_url:
        raise Exception('KEY_VAULT_URL environment variable is not configured')

    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

    try:
        arn = secret_client.get_secret(secret_name).value
        if not arn:
            raise Exception(f"Secret {secret_name} is empty in Key Vault")
        return arn
    except Exception as e:
        logging.error(f"Error retrieving ARN for {project} from Key Vault: {str(e)}")
        raise
"""
Shared authentication module for Azure Function endpoints.

Handles:
- Cognito credential retrieval from Azure Key Vault (cached)
- OAuth token acquisition from AWS Cognito (cached)

Used by the single GUID lookup and JSON bulk processing endpoints.
"""

import logging
import os
from datetime import datetime, timedelta
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import requests
from requests.auth import HTTPBasicAuth


# --- Token & Secret Caching Logic ---
_token_cache = {'access_token': None, 'expires_at': None}
_secrets_cache = {'client_id': None, 'client_secret': None}


def get_cached_token():
    """Return cached token if still valid (with 60s safety buffer)"""
    if _token_cache['access_token'] and _token_cache['expires_at']:
        if datetime.now() < _token_cache['expires_at'] - timedelta(seconds=60):
            return _token_cache['access_token']
    return None


def cache_token(access_token, expires_in):
    """Cache a token with its expiration time"""
    _token_cache['access_token'] = access_token
    _token_cache['expires_at'] = datetime.now() + timedelta(seconds=expires_in)


def get_cognito_credentials():
    """Retrieve Cognito credentials from Azure Key Vault (cached)"""
    if _secrets_cache['client_id'] and _secrets_cache['client_secret']:
        return _secrets_cache['client_id'], _secrets_cache['client_secret']

    try:
        key_vault_url = os.environ.get('KEY_VAULT_URL')
        client_id_secret_name = os.environ.get('COGNITO_CLIENT_ID_SECRET_NAME', 'cognito-client-id')
        client_secret_secret_name = os.environ.get('COGNITO_CLIENT_SECRET_SECRET_NAME', 'cognito-client-secret')

        if not key_vault_url:
            raise Exception('KEY_VAULT_URL environment variable is not configured')

        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

        client_id = secret_client.get_secret(client_id_secret_name).value
        client_secret = secret_client.get_secret(client_secret_secret_name).value

        _secrets_cache['client_id'] = client_id
        _secrets_cache['client_secret'] = client_secret
        return client_id, client_secret
    except Exception as e:
        logging.error(f'Error retrieving credentials from Key Vault: {str(e)}')
        raise


def get_cognito_token(client_id, client_secret):
    """Get OAuth token from Cognito (uses cache if valid)"""
    cached_token = get_cached_token()
    if cached_token:
        return cached_token

    cognito_domain = os.environ.get('COGNITO_DOMAIN')
    token_url = f'https://{cognito_domain}/oauth2/token'

    response = requests.post(
        token_url,
        auth=HTTPBasicAuth(client_id, client_secret),
        data={'grant_type': 'client_credentials'},
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=10
    )
    token_data = response.json()
    cache_token(token_data['access_token'], token_data.get('expires_in', 3600))
    return token_data['access_token']
