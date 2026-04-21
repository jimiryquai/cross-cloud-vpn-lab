import azure.functions as func
import json
import logging
import requests
import os
from shared.auth import get_cognito_credentials, get_cognito_token

app = func.FunctionApp()

# --- Helper Functions (Preserved for Integration Tests) ---
def call_guid_api(access_token, identifier, correlation_id):
    """ Calls upstream GUID API forwarding headers as per schema."""
    try:
        guid_api_base_url = os.environ.get('GUID_API_URL')
        if not guid_api_base_url:
            raise ValueError('GUID_API_URL environment variable is not configured')

        guid_api_url = f'{guid_api_base_url}/guid-translation-service/v1/dwp-guid'

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
            logging.error(
                f'Upstream Error: {response.status_code} - {response.text}'
            )
            raise RuntimeError(f'Upstream service returned {response.status_code}')

        return response.json()
    except requests.RequestException as e:
        raise ConnectionError(
            f'Failed to connect to upstream API: {str(e)}'
        ) from e


# --- API Routes ---

# 1. Single Lookup (GET)
@app.route(route="guid-translation-service/v1/dwp-guid", methods=["GET"])
def get_single_guid(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing single GUID lookup.')
    identifier = req.headers.get('Identifier')
    correlation_id = req.headers.get('correlation-id', 'not-provided')

    if not identifier:
        return func.HttpResponse(
            json.dumps({"error": "Missing required header: Identifier"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        client_id, client_secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, client_secret)

        person_data = call_guid_api(access_token, identifier, correlation_id)

        return func.HttpResponse(
            json.dumps({
                "Type": "NINO",
                "Returned identifier of the type specified in the type field": person_data.get('nino', 'NOT_FOUND')
            }),
            status_code=200,
            mimetype="application/json",
            headers={"correlation-id": correlation_id}
        )
    except Exception as e:
        logging.error(f'Proxy Failure: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


# 2. Bulk Processing (POST)
@app.route(route="dwp-guid-bulk-service/v1/{bulk_activity}", methods=["POST"])
def process_bulk_guids(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing bulk GUID translation.')
    bulk_activity = req.route_params.get('bulk_activity')
    correlation_id = req.headers.get('correlation-id', 'not-provided')

    try:
        req_body = req.get_json()
        if req_body.get('numberOfRecords', 0) > 5000:
            return func.HttpResponse(
                json.dumps({
                    "status": "400 BAD_REQUEST",
                    "messages": ["Batch exceeds 5,000 records"]
                }),
                status_code=400,
                mimetype="application/json"
            )

        client_id, client_secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, client_secret)

        bulk_api_url = f"{os.environ.get('GUID_API_URL')}/dwp-guid-bulk-service/v1/{bulk_activity}"

        response = requests.post(
            bulk_api_url,
            headers={
                'Authorization': f'Bearer {access_token}',
                'correlation-id': correlation_id
            },
            json=req_body,
            timeout=30
        )

        req_body = None  # Discard original NINOs immediately from memory

        return func.HttpResponse(
            response.text if response.status_code == 200 else json.dumps(response.json()),
            status_code=response.status_code,
            mimetype="application/json"
        )
    except ValueError:
        return func.HttpResponse(
            json.dumps({
                "status": "400 BAD_REQUEST",
                "messages": ["Invalid JSON payload"]
            }),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({
                "status": "500 ERROR",
                "messages": [str(e)]
            }),
            status_code=500,
            mimetype="application/json"
        )


# 3. Daily Allowance (GET)
@app.route(route="dwp-guid-bulk-service/v1/remaining-daily-allowance", methods=["GET"])
def get_daily_allowance(req: func.HttpRequest) -> func.HttpResponse:
    # Temporarily mocked so the Custom Connector doesn't fail during testing
    return func.HttpResponse("10000", status_code=200)