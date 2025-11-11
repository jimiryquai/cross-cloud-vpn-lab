import logging
import json
import os
import time
from datetime import datetime, timedelta
import azure.functions as func
import boto3
from botocore.exceptions import ClientError
import requests
from requests.auth import HTTPBasicAuth

# Token cache (in-memory)
_token_cache = {
    'access_token': None,
    'expires_at': None
}

def get_cached_token():
    """Get cached token if valid, otherwise return None"""
    if _token_cache['access_token'] and _token_cache['expires_at']:
        # Check if token is still valid (with 60 second buffer)
        if datetime.now() < _token_cache['expires_at'] - timedelta(seconds=60):
            logging.info('Using cached Cognito token')
            return _token_cache['access_token']
    return None

def cache_token(access_token, expires_in):
    """Cache token with expiration time"""
    _token_cache['access_token'] = access_token
    _token_cache['expires_at'] = datetime.now() + timedelta(seconds=expires_in)
    logging.info(f'Cached token, expires at {_token_cache["expires_at"]}')

def get_cognito_credentials():
    """Retrieve Cognito credentials from AWS Secrets Manager"""
    try:
        # Get AWS credentials from environment
        aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_region = os.environ.get('AWS_REGION', 'eu-west-2')
        secret_name = os.environ.get('AWS_SECRET_NAME', 'consumer/cognito/vpn-lab/credentials')

        if not aws_access_key_id or not aws_secret_access_key:
            raise Exception('AWS credentials not configured')

        # Create Secrets Manager client
        secrets_client = boto3.client(
            'secretsmanager',
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

        # Retrieve secret
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])

        logging.info(f'Retrieved credentials from AWS Secrets Manager: {secret_name}')
        return secret_data['client_id'], secret_data['secret']

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logging.error(f'AWS ClientError: {error_code}')
        raise Exception(f'Failed to retrieve credentials from AWS: {error_code}')
    except Exception as e:
        logging.error(f'Error retrieving credentials: {str(e)}')
        raise

def get_cognito_token(client_id, client_secret):
    """Get OAuth token from Cognito using client credentials flow"""

    # Check cache first
    cached_token = get_cached_token()
    if cached_token:
        return cached_token

    try:
        # Get Cognito domain from environment
        cognito_domain = os.environ.get('COGNITO_DOMAIN')
        if not cognito_domain:
            raise Exception('COGNITO_DOMAIN not configured')

        # Cognito token endpoint
        token_url = f'https://{cognito_domain}/oauth2/token'

        # Make token request
        logging.info(f'Requesting token from Cognito: {token_url}')
        response = requests.post(
            token_url,
            auth=HTTPBasicAuth(client_id, client_secret),
            data={'grant_type': 'client_credentials'},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )

        if response.status_code != 200:
            logging.error(f'Cognito token request failed: {response.status_code} - {response.text}')
            raise Exception(f'Cognito authentication failed: {response.status_code}')

        token_data = response.json()
        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600)

        # Cache the token
        cache_token(access_token, expires_in)

        logging.info('Successfully obtained Cognito token')
        return access_token

    except requests.RequestException as e:
        logging.error(f'HTTP error calling Cognito: {str(e)}')
        raise Exception(f'Failed to call Cognito: {str(e)}')
    except Exception as e:
        logging.error(f'Error getting Cognito token: {str(e)}')
        raise

def call_guid_api(access_token, guid):
    """Call GUID API with Bearer token to retrieve person details"""
    try:
        # Get GUID API base URL from environment
        guid_api_base_url = os.environ.get('GUID_API_URL')
        if not guid_api_base_url:
            raise Exception('GUID_API_URL not configured')

        # Construct full URL with GUID as path parameter
        # Expected format: https://...amazonaws.com/test/nino/{guid}
        guid_api_url = f'{guid_api_base_url}/nino/{guid}'

        # Make API request (GET method with path parameter)
        logging.info(f'Calling GUID API: {guid_api_url}')
        response = requests.get(
            guid_api_url,
            headers={
                'Authorization': f'Bearer {access_token}'
            },
            timeout=10
        )

        if response.status_code != 200:
            logging.error(f'GUID API request failed: {response.status_code} - {response.text}')
            raise Exception(f'GUID API call failed: {response.status_code}')

        person_data = response.json()
        logging.info('Successfully retrieved person details from GUID')
        return person_data

    except requests.RequestException as e:
        logging.error(f'HTTP error calling GUID API: {str(e)}')
        raise Exception(f'Failed to call GUID API: {str(e)}')
    except Exception as e:
        logging.error(f'Error calling GUID API: {str(e)}')
        raise

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to get person details from GUID.
    Handles complete OAuth flow transparently.
    """
    logging.info('GetGUID function processing request')

    try:
        # Parse request body
        try:
            req_body = req.get_json()
            guid = req_body.get('guid')
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                mimetype="application/json",
                status_code=400
            )

        # Validate GUID parameter
        if not guid:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter: guid"}),
                mimetype="application/json",
                status_code=400
            )

        if not isinstance(guid, str) or len(guid) < 32:
            return func.HttpResponse(
                json.dumps({"error": "Invalid GUID format"}),
                mimetype="application/json",
                status_code=400
            )

        # Step 1: Get Cognito credentials from AWS Secrets Manager
        logging.info('Step 1: Retrieving Cognito credentials from AWS Secrets Manager')
        client_id, client_secret = get_cognito_credentials()

        # Step 2: Get OAuth token from Cognito
        logging.info('Step 2: Getting OAuth token from Cognito')
        access_token = get_cognito_token(client_id, client_secret)

        # Step 3: Call GUID API to get person details
        logging.info('Step 3: Calling GUID API to retrieve person details')
        person_data = call_guid_api(access_token, guid)

        # Return person data (includes NINO)
        return func.HttpResponse(
            json.dumps(person_data),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f'Error in GetGUID: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
