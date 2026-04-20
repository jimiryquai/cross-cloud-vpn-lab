import logging
import json
import os
import azure.functions as func
import requests

from shared.auth import (
    get_cognito_credentials,
    get_cognito_token,
    get_cached_token,
    cache_token,
    _token_cache,
    _secrets_cache
)


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