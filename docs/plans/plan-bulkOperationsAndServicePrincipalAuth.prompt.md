# Plan: Add Bulk Operations & Service Principal Auth to GUID Connector

## TL;DR
Extend the existing custom connector with two new operations (CSV bulk translate + daily allowance) by adding new Azure Function endpoints. The bulk translate function accepts a full CSV string, handles NINO→GUID translation internally (parsing, chunking, calling AWS bulk API, rebuilding CSV), and returns the modified CSV — using an async pattern to avoid connector timeouts. Simultaneously migrate auth from API key to Entra ID service principal. Update docs to match.

---

## Phase 1: Extract Shared Auth Module

The existing `GetGUID/__init__.py` contains OAuth orchestration logic (Cognito creds retrieval, token caching, token acquisition) that all three functions will share. Extract it into a shared module.

1. Create `azure-function/shared/__init__.py` — empty init
2. Create `azure-function/shared/auth.py` — move these functions from `GetGUID/__init__.py`:
   - `_token_cache` dict, `get_cached_token()`, `cache_token()`
   - `get_cognito_credentials()` (boto3 Secrets Manager call)
   - `get_cognito_token()` (Cognito OAuth client_credentials flow)
3. Update `GetGUID/__init__.py` to import from `shared.auth` instead of defining locally

**Verification:** Existing unit tests in `azure-function/tests/test_unit.py` should still pass after refactor.

---

## Phase 2: New Azure Function — ProcessCSV (Bulk Translate)

A CSV-in / CSV-out function that handles all heavy data processing. Uses async pattern (returns 202 → poll for result) to avoid connector timeout.

4. Create `azure-function/ProcessCSV/function.json`:
   - `authLevel`: "function" (changes to "anonymous" in Phase 4)
   - `methods`: ["post"]
   - `route`: "process-csv/v1/translate"
5. Create `azure-function/ProcessCSV/__init__.py` — main entry point:
   - Accept POST with JSON body: `{ csvContent: string, ninoColumn: string, activity: "TRANSFORM_NINO_TO_DWP_GUID" | "TRANSFORM_DWP_GUID_TO_NINO" }`
   - `correlation-id` header (required)
   - Async pattern: store job in-memory (or Azure Table/Blob), return `202 Accepted` with `Location` header pointing to status endpoint
   - Kick off processing (see step 6)
6. Create `azure-function/ProcessCSV/processor.py` — core processing logic:
   - Parse CSV string (Python `csv` module from `io.StringIO`)
   - Identify the NINO/GUID column by name (`ninoColumn` param)
   - Extract identifier values from that column
   - Chunk into batches of 5,000
   - For each chunk: build `recordHolder` JSON → call AWS bulk API with Bearer token (via shared auth) → collect results
   - Build NINO→GUID mapping from all chunk results
   - Replace identifier values in the original CSV column
   - Rebuild CSV string with `\r\n` line endings (to match expected format for OOB import)
   - Store result and mark job complete
7. Create `azure-function/ProcessCSV/status.json` + `status.py` — status/polling endpoint:
   - `route`: "process-csv/v1/status/{jobId}"
   - `methods`: ["get"]
   - Returns `200` with `{ status: "complete", csvContent: "..." }` or `{ status: "processing" }` or `{ status: "failed", error: "..." }`

**Key design details:**
- `requests` timeout per bulk API call: 120s (5k records could be slow)
- Total function timeout: 10 minutes (set in host.json)
- Job storage: simplest option is `dict` in-memory (fine for single-instance Consumption plan); upgrade to Azure Blob Storage if persistence needed
- CSV line endings preserved as `\r\n`

---

## Phase 3: New Azure Function — Daily Allowance

8. Create `azure-function/DailyAllowance/function.json`:
   - `authLevel`: "function"
   - `methods`: ["get"]
   - `route`: "dwp-guid-bulk-service/v1/remaining-daily-allowance"
9. Create `azure-function/DailyAllowance/__init__.py`:
   - Extract `correlation-id` from header (required)
   - Call shared auth for Bearer token
   - GET `{GUID_API_URL}/dwp-guid-bulk-service/v1/remaining-daily-allowance` with auth + correlation headers
   - Return upstream response passthrough

---

## Phase 4: Auth Migration — API Key → Service Principal (Entra ID)

Switch the Power Platform → Azure Function auth layer from function key to Entra ID OAuth2 client credentials.

10. **Entra ID App Registration** (manual/scripted):
    - Register app for the Azure Function (API app)
    - Define an app role or scope (e.g. `GuidService.ReadWrite`)
    - Register a second app for Power Platform (client app) — or use an existing service principal
    - Grant the client app permission to the API app
    - Admin consent the permission
11. **Azure Function EasyAuth configuration**:
    - Enable Authentication on the Function App
    - Add Entra ID as identity provider using the API app registration
    - Set `authLevel` to "anonymous" in all three function.json files (EasyAuth handles auth before the function is invoked)
12. **Update connector security definition** in the swagger from `apiKey` to OAuth2 client credentials:
    - `securityDefinitions` changes from `apiKey` type to `oauth2` with `flow: "application"` (client credentials)
    - `tokenUrl`: `https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token`
    - Scope: `api://{api-app-client-id}/.default`
13. **Update connector connection parameters** — replace `api_key` securestring with:
    - `client_id` (string)
    - `client_secret` (securestring)
    - `tenant_id` (string)
14. **Azure Function environment variables** — configure the following app settings:
    - `FUNCTION_APP_URL` — the base URL of the Function App (e.g. `https://vpn-lab-aws-bridge-5295.azurewebsites.net`)
    - `SP_CLIENT_ID` — the service principal client ID for downstream auth
    - `SP_CLIENT_SECRET` — **stored in Azure Key Vault** and accessed via Key Vault secret reference:
      ```
      @Microsoft.KeyVault(SecretUri=https://<vault-name>.vault.azure.net/secrets/sp-client-secret/)
      ```
      This means the Function App setting value is a Key Vault reference, not the secret itself. The Function App's managed identity must have `Get` secret permission on the Key Vault.
    - `SP_TENANT_ID` — the Entra ID tenant ID

---

## Phase 5: Update Connector Swagger Definition

14. Update `updated-connector-swagger.json` with:
    - **New operation** `ProcessCSV` (POST `/process-csv/v1/translate`):
      - Header: `correlation-id` (required, UUID)
      - Body: `{ csvContent: string, ninoColumn: string, activity: string (enum) }`
      - Response: 202 with `Location` header (job status URL)
    - **New operation** `GetProcessingStatus` (GET `/process-csv/v1/status/{jobId}`):
      - Path param: `jobId` (string)
      - Response: 200 with `{ status: string, csvContent?: string, error?: string }`
    - **New operation** `GetDailyAllowance` (GET `/dwp-guid-bulk-service/v1/remaining-daily-allowance`):
      - Header: `correlation-id` (required)
      - Response: 200 (string)
    - **New definitions**: `ProcessCSVRequest`, `ProcessingStatusResponse`, `error` schemas
    - **Updated securityDefinitions** per Phase 4

---

## Phase 6: Tests

15. Add unit tests for `ProcessCSV` function:
    - CSV parsing with various delimiters and encodings
    - Correct column identified and values extracted
    - Chunking logic (50k rows → 10 × 5k)
    - NINO→GUID replacement in correct column, other columns untouched
    - CSV rebuilt with \r\n line endings
    - Async job lifecycle (submit → processing → complete/failed)
    - Mock upstream bulk API calls
16. Add unit tests for `DailyAllowance` function
17. Add unit test for shared auth module extraction (ensure token caching still works)
18. Update integration tests in `azure-function/tests/test_integration.py` for new endpoints

---

## Phase 7: Documentation Updates

19. Update `docs/README.md` — add bulk operations to feature list
20. Update `docs/CROSS-CLOUD-OAUTH-GUIDE.md` — update architecture diagram and component reference (auth flow, new endpoints)
21. Update `docs/HANDOVER.md` — add bulk endpoint details and auth change notes
22. Update `docs/QUICK-REFERENCE-CARD.md` — add bulk curl examples
23. Update `docs/CONNECTOR-COMPARISON.md` — reflect auth change from API key to service principal
24. Update `docs/TEST-STRATEGY.md` — add bulk test scenarios

---

## Relevant Files

- `azure-function/GetGUID/__init__.py` — refactor to extract shared auth (Phase 1)
- `azure-function/GetGUID/function.json` — change authLevel to anonymous (Phase 4)
- `azure-function/shared/auth.py` — NEW: shared OAuth/token module (Phase 1)
- `azure-function/ProcessCSV/__init__.py` — NEW: CSV translate entry point, async job management (Phase 2)
- `azure-function/ProcessCSV/processor.py` — NEW: CSV parse, chunk, translate, rebuild logic (Phase 2)
- `azure-function/ProcessCSV/function.json` — NEW: POST trigger binding (Phase 2)
- `azure-function/ProcessCSV/status.py` — NEW: polling endpoint for job status (Phase 2)
- `azure-function/ProcessCSV/status.json` — NEW: GET trigger binding for status (Phase 2)
- `azure-function/DailyAllowance/__init__.py` — NEW: allowance proxy function (Phase 3)
- `azure-function/DailyAllowance/function.json` — NEW: allowance function binding (Phase 3)
- `azure-function/host.json` — set functionTimeout to 10 minutes (Phase 2)
- `updated-connector-swagger.json` — add operations, schemas, update auth (Phase 5)
- `power-platform/solution/Connectors/jr_getnino_connectionparameters.json` — update auth params (Phase 4)
- `power-platform/solution/Connectors/jr_getnino_openapidefinition.json` — update with new operations (Phase 5)
- `azure-function/tests/test_unit.py` — add ProcessCSV + allowance tests (Phase 6)
- `azure-function/tests/test_integration.py` — add integration tests (Phase 6)
- `docs/` — all doc files updated (Phase 7)

## Verification

1. Run `pytest azure-function/tests/test_unit.py` — existing tests pass after shared auth extraction
2. Run `pytest azure-function/tests/test_unit.py` — new ProcessCSV and allowance tests pass
3. Deploy function to Azure, confirm all routes respond (manual or integration test)
4. Submit a test CSV (small, e.g. 10 rows) → poll status → receive modified CSV with GUIDs
5. Submit a 50k row CSV → verify chunking (10 × 5k) and full round-trip completes within 10 min
6. Import updated swagger → verify operations appear in connector
7. Test connector with service principal auth → confirm connection creation works
8. End-to-end: Canvas App upload → flow validates → connector calls ProcessCSV → polls for result → feeds to OOB import

## Decisions

- **Combined connector**: Single connector with 4 operations (single lookup, process CSV, check status, daily allowance)
- **No APIM**: Direct Function path only
- **Auth migration scope**: Applies to all operations at once (EasyAuth is function-app-wide)
- **Processing in Function**: CSV parsing, chunking, bulk API calls, and CSV reconstruction all happen in Python — Power Automate only does simple validation and orchestration
- **Validation split**: Simple checks (headers, config records, date range vs Dataverse) stay in Power Automate. Heavy data transformation happens in Function
- **Async pattern**: Function returns 202 + Location header, flow polls status endpoint via "Do Until" loop
- **Shared module pattern**: Extract auth into `shared/auth.py` to avoid code duplication
- **Function timeout**: 10 minutes in host.json; `requests` timeout 120s per bulk API call
- **Job storage**: In-memory dict (single Consumption plan instance); upgrade to Blob if persistence needed
- **CSV format**: Function preserves \r\n line endings for OOB import compatibility
- **Environment variables**: Function URL, SP client ID, and SP tenant ID stored as plain app settings. SP client secret stored in Azure Key Vault and accessed via Key Vault secret reference in app settings (requires managed identity with Key Vault `Get` secret permission)

## End-to-End Flow

```
1. User uploads CSV via attachment control in Canvas App
2. Canvas App triggers Power Automate flow with blob URL
3. Flow file input parameter converts blob → base64 → decodes to string
4. Flow validates: header checks, config record checks, date range checks vs Dataverse
5. Flow calls ProcessCSV connector action with { csvContent, ninoColumn, activity }
6. Function returns 202 Accepted + Location: /process-csv/v1/status/{jobId}
7. Flow enters "Do Until" loop, polling status endpoint every N seconds
8. Function (background): parse CSV → extract NINOs → chunk 5k → bulk translate all → replace → rebuild CSV
9. Status returns { status: "complete", csvContent: "...modified CSV..." }
10. Flow feeds modified CSV to OOB Dataverse import:
    - ParseImport → TransformImport → ImportRecordsImport
```

## Open Design Decisions

### ⛔ BLOCKER: Cognito Credential Storage Location

**Status: AWAITING DECISION — implementation on hold until resolved.**

The Azure Function needs Cognito `client_id` and `client_secret` to authenticate with the AWS GUID API (OAuth2 client credentials flow via AWS Cognito). There are two options for where these credentials are stored:

| | **Option A: AWS Secrets Manager (current)** | **Option B: Azure Key Vault** |
|---|---|---|
| **How it works** | Function uses `boto3` to call AWS Secrets Manager via IAM credentials (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` as env vars) | Function reads Cognito creds from Azure Key Vault via managed identity or Key Vault secret reference in app settings |
| **Pros** | Already implemented and working; credentials managed on the AWS side where Cognito lives | Single secrets store on the Azure side; no AWS IAM credentials needed in the Function; simpler dependency chain; aligns with storing the SP client secret in Key Vault too |
| **Cons** | Requires AWS IAM credentials stored in the Function App (widens the credential surface); adds boto3 + AWS SDK as a dependency | Requires someone to sync Cognito creds into Key Vault if they rotate on the AWS side; adds a cross-cloud operational dependency |
| **Impact on code** | No change (existing `shared/auth.py` uses boto3) | Refactor `get_cognito_credentials()` in `shared/auth.py` to read from Key Vault (or from app settings via Key Vault references) instead of boto3. Could potentially remove `boto3` dependency entirely |

**This decision affects:**
- Phase 1 (shared auth module design)
- Phase 2 (ProcessCSV dependencies)
- `azure-function/requirements.txt` (boto3 may be removable)
- Azure Function app settings configuration

**Action required:** Confirm with the infrastructure/security team which approach is being taken before proceeding with implementation.

---

## Further Considerations

1. ~~APIM~~ — **Not using APIM.** Direct Function path only.
2. **Async fallback risk**: In-memory job storage is lost if the Function instance recycles mid-processing. For production, consider Azure Blob Storage for job state. Consumption plan cold starts could also affect polling. *Recommend: start with in-memory, move to Blob if reliability issues emerge.*
3. **Power Platform connector timeout**: Handled by async pattern — initial POST returns instantly (202), polling GETs are fast. No timeout risk.
4. **CSV size in connector request body**: 50k rows of CSV as a JSON string could be several MB. Power Platform connector request body limit is ~100MB, so this is fine, but large payloads may slow the initial POST. *Recommend: test with realistic 50k CSV to confirm.*
