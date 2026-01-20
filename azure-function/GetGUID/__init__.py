import logging
import json
import os
from datetime import datetime, timedelta
import azure.functions as func
import boto3
from botocore.exceptions import ClientError
import requests
from requests.auth import HTTPBasicAuth

# --- Token Caching Logic ---
_token_cache = {'access_token': None, 'expires_at': None}

def get_cached_token():
    if _token_cache['access_token'] and _token_cache['expires_at']:
        if datetime.now() < _token_cache['expires_at'] - timedelta(seconds=60):
            return _token_cache['access_token']
    return None

def cache_token(access_token, expires_in):
    _token_cache['access_token'] = access_token
    _token_cache['expires_at'] = datetime.now() + timedelta(seconds=expires_in)

def get_cognito_credentials():
    """Retrieve Cognito credentials from AWS Secrets Manager"""
    try:
        aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_region = os.environ.get('AWS_REGION', 'eu-west-2')
        secret_name = os.environ.get('AWS_SECRET_NAME', 'consumer/cognito/vpn-lab/credentials')

        secrets_client = boto3.client(
            'secretsmanager',
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        return secret_data['client_id'], secret_data['secret']
    except Exception as e:
        logging.error(f'Error retrieving credentials: {str(e)}')
        raise

def get_cognito_token(client_id, client_secret):
    """Get OAuth token from Cognito"""
    cached_token = get_cached_token()
    if cached_token: return cached_token

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

def call_guid_api(access_token, identifier, correlation_id):
    """ Calls upstream GUID API forwarding headers as per schema."""
    try:
        guid_api_base_url = os.environ.get('GUID_API_URL')
        if not guid_api_base_url:
            raise Exception('GUID_API_URL environment variable is not configured')

        # Use the path defined in the official OpenAPI schema
        guid_api_url = f'{guid_api_base_url}/guid-translation-service/v1/dwp-guid'

        logging.info(f'Calling upstream GUID API at: {guid_api_url}')
        
        # Forward the Identifier and correlation-id in HEADERS
        response = requests.get(
            guid_api_url,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Identifier': identifier,
                'correlation-id': correlation_id
            },
            timeout=10
        )

        if response.status_code != 200:
            logging.error(f'Upstream Error: {response.status_code} - {response.text}')
            raise Exception(f'Upstream service returned {response.status_code}')

        return response.json()

    except requests.RequestException as e:
        logging.error(f'HTTP connection error: {str(e)}')
        raise Exception(f'Failed to connect to upstream API: {str(e)}')

def main(req: func.HttpRequest) -> func.HttpResponse:
    """ Azure Function Entry Point - pulls from headers and returns IdentityResponseDTO."""
    logging.info('GetGUID Proxy processing request')

    try:
        # 1. Pull parameters from HEADERS to match the Custom Connector/Schema
        identifier = req.headers.get('Identifier')
        correlation_id = req.headers.get('correlation-id', 'not-provided')

        if not identifier:
            return func.HttpResponse(
                json.dumps({"error": "Missing required header: Identifier"}),
                mimetype="application/json",
                status_code=400
            )

        # 2. Handle Security & Tokens
        client_id, client_secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, client_secret)

        # 3. Call Upstream Service
        person_data = call_guid_api(access_token, identifier, correlation_id)

        # 4. Map to the specific IdentityResponseDTO JSON structure
        response_payload = {
            "Type": "NINO",
            "Returned identifier of the type specified in the type field": person_data.get('nino', 'NOT_FOUND')
        }

        return func.HttpResponse(
            json.dumps(response_payload),
            mimetype="application/json",
            status_code=200,
            headers={"correlation-id": correlation_id}
        )

    except Exception as e:
        logging.error(f'Proxy Failure: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
    