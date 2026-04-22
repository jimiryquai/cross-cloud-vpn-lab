
import azure.functions as func
import json
import logging
from shared.context_logger import ContextLogger
import requests
import os
from shared.auth.secret import get_cognito_credentials
from shared.auth.token import get_cognito_token
from pydantic import BaseModel, ValidationError, Field
from typing import Optional, List
from middleware.project_context import project_context_middleware
# --- Environment Variable Validation ---
REQUIRED_ENV_VARS = [
    "KEY_VAULT_URL",
    "COGNITO_DOMAIN",
    "GUID_API_URL",
]

def validate_env_vars():
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

# Validate environment at startup
validate_env_vars()
# --- API Routes ---

# --- Input Schemas ---
class BulkGuidRequest(BaseModel):
    numberOfRecords: int = Field(..., ge=1, le=5000)
    identifiers: List[str]

class SingleGuidRequestHeaders(BaseModel):
    Identifier: str
    correlation_id: Optional[str] = None

class ProjectQueryParams(BaseModel):
    project: str


logger = ContextLogger()
app = func.FunctionApp()


# --- Helper Functions (Preserved for Integration Tests) ---
def call_guid_api(access_token, identifier, correlation_id):
    """Calls upstream GUID API forwarding headers as per schema."""
    try:
        guid_api_base_url = os.environ.get("GUID_API_URL")
        if not guid_api_base_url:
            raise ValueError("GUID_API_URL environment variable is not configured")

        guid_api_url = f"{guid_api_base_url}/guid-translation-service/v1/dwp-guid"

        response = requests.get(
            guid_api_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Identifier": identifier,
                "correlation-id": correlation_id,
            },
            timeout=10,
        )


        if response.status_code != 200:
            logger.error(f"Upstream Error: {response.status_code} - {response.text}", project=None, correlation_id=correlation_id)
            raise RuntimeError(f"Upstream service returned {response.status_code}")

        return response.json()
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to connect to upstream API: {str(e)}") from e


# --- API Routes ---


# 1. Single Lookup (GET)

@app.route(route="guid-translation-service/v1/dwp-guid", methods=["GET"])
@project_context_middleware
def get_single_guid(req: func.HttpRequest) -> func.HttpResponse:
    # Validate headers
    try:
        headers = SingleGuidRequestHeaders(
            Identifier=req.headers.get("Identifier"),
            correlation_id=req.headers.get("correlation-id", "not-provided")
        )
    except ValidationError as ve:
        return func.HttpResponse(
            json.dumps({"error": ve.errors()}),
            status_code=400,
            mimetype="application/json",
        )

    project = req.context["project"]
    arn = req.context["arn"]
    correlation_id = req.context["correlation_id"]
    logger.info("Processing single GUID lookup.", project=project, correlation_id=correlation_id)

    try:
        # (Placeholder) Use arn as needed for downstream logic
        client_id, client_secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, client_secret)
        person_data = call_guid_api(access_token, headers.Identifier, correlation_id)

        return func.HttpResponse(
            json.dumps(
                {
                    "Type": "NINO",
                    "Returned identifier of the type specified in the type field": person_data.get(
                        "nino", "NOT_FOUND"
                    ),
                }
            ),
            status_code=200,
            mimetype="application/json",
            headers={"correlation-id": correlation_id},
        )
    except Exception as e:
        logger.error(f"Proxy Failure: {str(e)}", project=project, correlation_id=correlation_id)
        return func.HttpResponse(
            json.dumps({"error": str(e)}), status_code=500, mimetype="application/json"
        )


# 2. Bulk Processing (POST)

@app.route(route="dwp-guid-bulk-service/v1/{bulk_activity}", methods=["POST"])
@project_context_middleware
def process_bulk_guids(req: func.HttpRequest) -> func.HttpResponse:
    project = req.context["project"]
    arn = req.context["arn"]
    correlation_id = req.context["correlation_id"]
    bulk_activity = req.route_params.get("bulk_activity")
    logger.info("Processing bulk GUID translation.", project=project, correlation_id=correlation_id)

    # Validate JSON body
    try:
        req_body_json = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"status": "400 BAD_REQUEST", "messages": ["Invalid JSON payload"]}),
            status_code=400,
            mimetype="application/json",
        )
    try:
        validated_body = BulkGuidRequest(**req_body_json)
    except ValidationError as ve:
        return func.HttpResponse(
            json.dumps({"status": "400 BAD_REQUEST", "messages": ve.errors()}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        client_id, client_secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, client_secret)

        bulk_api_url = (
            f"{os.environ.get('GUID_API_URL')}/dwp-guid-bulk-service/v1/{bulk_activity}"
        )

        response = requests.post(
            bulk_api_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "correlation-id": correlation_id,
            },
            json=validated_body.dict(),
            timeout=30,
        )

        req_body_json = None  # Discard original NINOs immediately from memory

        return func.HttpResponse(
            (
                response.text
                if response.status_code == 200
                else json.dumps(response.json())
            ),
            status_code=response.status_code,
            mimetype="application/json",
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"status": "500 ERROR", "messages": [str(e)]}),
            status_code=500,
            mimetype="application/json",
        )

# 3. Daily Allowance (GET)
@app.route(route="dwp-guid-bulk-service/v1/remaining-daily-allowance", methods=["GET"])
@project_context_middleware
def get_daily_allowance(req: func.HttpRequest) -> func.HttpResponse:
    project = req.context["project"]
    arn = req.context["arn"]
    correlation_id = req.context["correlation_id"]
    logger.info("Processing daily allowance check via upstream proxy.", project=project, correlation_id=correlation_id)

    try:
        # Auth & Tokens
        client_id, client_secret = get_cognito_credentials()
        access_token = get_cognito_token(client_id, client_secret)

        # Build URL based on the exact Swagger definition
        allowance_api_url = f"{os.environ.get('GUID_API_URL')}/dwp-guid-bulk-service/v1/remaining-daily-allowance"

        # Call Upstream AWS Service
        response = requests.get(
            allowance_api_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "correlation-id": correlation_id,
            },
            timeout=10,
        )

        # The Swagger contract expects a simple string return for 200 OK
        if response.status_code == 200:
            return func.HttpResponse(response.text, status_code=200)
        else:
            # Pass back the exact error AWS throws
            return func.HttpResponse(
                json.dumps(response.json()),
                status_code=response.status_code,
                mimetype="application/json",
            )

    except Exception as e:
        logger.error(f"Allowance proxy failure: {str(e)}", project=project, correlation_id=correlation_id)
        return func.HttpResponse(
            json.dumps({"status": "500 ERROR", "messages": [str(e)]}),
            status_code=500,
            mimetype="application/json",
        )
