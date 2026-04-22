import os
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth

_token_cache = {'access_token': None, 'expires_at': None}

def get_cached_token():
    """Return cached token if still valid (with 60s safety buffer)"""
    if _token_cache['access_token'] and _token_cache['expires_at']:
        if datetime.now() < _token_cache['expires_at'] - timedelta(seconds=60):
            return _token_cache['access_token']
    return None

def cache_token(access_token, expires_in):
    _token_cache['access_token'] = access_token
    _token_cache['expires_at'] = datetime.now() + timedelta(seconds=expires_in)

def get_cognito_token(client_id, client_secret, requests_session=None):
    """Get OAuth token from Cognito (uses cache if valid)"""
    cached_token = get_cached_token()
    if cached_token:
        return cached_token

    cognito_domain = os.environ.get('COGNITO_DOMAIN')
    token_url = f'https://{cognito_domain}/oauth2/token'

    session = requests_session or requests
    response = session.post(
        token_url,
        auth=HTTPBasicAuth(client_id, client_secret),
        data={'grant_type': 'client_credentials'},
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=10
    )
    token_data = response.json()
    cache_token(token_data['access_token'], token_data.get('expires_in', 3600))
    return token_data['access_token']
