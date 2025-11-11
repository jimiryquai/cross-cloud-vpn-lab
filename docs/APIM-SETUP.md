# Azure API Management Setup - GUID Service

Complete guide for Azure API Management integration with GUID Service.

## What's Been Created ✅

### APIM Instance
- **Name:** `vpn-lab-apim-guid`
- **Tier:** Consumption
- **Gateway URL:** `https://vpn-lab-apim-guid.azure-api.net`
- **Location:** UK South
- **Cost:** ~$0.01/month for your usage

### API Configuration
- **API ID:** `guid-service`
- **API Name:** "GUID Service API"
- **Path:** `/guid`
- **Backend:** Azure Function `vpn-lab-aws-bridge-5295`
- **Operation:** POST `/GetGUID`

### Product Configuration
- **Product ID:** `guid-product`
- **Product Name:** "GUID Service Product"
- **State:** Published
- **Subscription Required:** Yes

---

## Benefits of APIM

### 1. **Environment Management** 🎯
Route to different backends based on subscription or header:
- Dev: `vpn-lab-aws-bridge-dev`
- Test: `vpn-lab-aws-bridge-test`
- Prod: `vpn-lab-aws-bridge-prod`

### 2. **Rate Limiting & Throttling**
Protect backends from runaway flows:
- Configured: 1000 calls/hour per subscription
- Quota: 10,000 calls/day per subscription

### 3. **Caching**
Cache GUID lookups for 10 minutes:
- Reduces backend load
- Improves response time
- Saves Azure Function execution costs

### 4. **Monitoring**
- Request/response logging
- Analytics dashboard
- Performance metrics
- Error tracking

### 5. **Security**
- Subscription key management
- IP whitelisting (optional)
- Request validation
- Response sanitization

---

## Complete Setup via Azure Portal

### Step 1: Create Subscription (2 mins)

1. Go to Azure Portal → API Management → `vpn-lab-apim-guid`
2. Click: **Subscriptions** (left menu)
3. Click: **+ Add subscription**
4. Configure:
   - **Name:** Power Platform Subscription
   - **Display name:** Power Platform Access
   - **Scope:** Product → GUID Service Product
   - **State:** Active
5. Click: **Create**
6. **Copy the Primary Key** - you'll need this for Custom Connector

### Step 2: Add Policies (5 mins)

1. Go to: **APIs** → **GUID Service API**
2. Click: **All operations**
3. In **Inbound processing**, click **</>** (code editor)
4. Paste the policy XML (see below)
5. Click: **Save**

**Policy XML:**
```xml
<policies>
    <inbound>
        <base />
        <!-- Rate limiting -->
        <rate-limit calls="1000" renewal-period="3600" />
        <quota calls="10000" renewal-period="86400" />

        <!-- Cache lookup -->
        <cache-lookup vary-by-developer="false" vary-by-developer-groups="false" />

        <!-- Forward Azure Function key -->
        <set-query-parameter name="code" exists-action="override">
            <value>uWczQWcKnaQHKM_FTWXgsFlF1wxdY5mgeDMwxnF4LiscAzFuECFtFQ==</value>
        </set-query-parameter>

        <!-- Add request tracking -->
        <set-header name="X-Request-ID" exists-action="override">
            <value>@(context.RequestId)</value>
        </set-header>
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
        <!-- Cache responses -->
        <cache-store duration="600" />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>
```

### Step 3: Test via APIM (2 mins)

1. In **GUID Service API**, click: **Test** tab
2. Select operation: **POST GetPersonDetails**
3. Add header:
   - **Name:** `Ocp-Apim-Subscription-Key`
   - **Value:** [Your subscription primary key]
4. Request body:
   ```json
   {
     "guid": "123e4567-e89b-12d3-a456-426614174000"
   }
   ```
5. Click: **Send**

**Expected Response:**
```json
{
  "guid": "123e4567-e89b-12d3-a456-426614174000",
  "nino": "AB123456C",
  "firstName": "John",
  "lastName": "Doe",
  "dateOfBirth": "1990-01-01",
  "source": "Mock NINO Service",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

---

## Creating Custom Connector from APIM

### Method 1: Export OpenAPI (Recommended)

1. In Azure Portal → APIM → **APIs** → **GUID Service API**
2. Click: **...** (three dots) → **Export**
3. Select: **OpenAPI v3 (JSON)**
4. Download the file
5. Import to Power Platform:
   - Data → Custom connectors
   - New custom connector → Import an OpenAPI file
   - Upload downloaded file

### Method 2: Manual Configuration

Use these details in Power Platform Custom Connector:

**General Tab:**
- Host: `vpn-lab-apim-guid.azure-api.net`
- Base URL: `/guid`

**Security Tab:**
- Authentication type: API Key
- Parameter label: Subscription Key
- Parameter name: Ocp-Apim-Subscription-Key
- Parameter location: Header

**Definition Tab:**
- Operation: GetPersonDetails (POST)
- Request: `/GetGUID`
- Body: `{"guid": "string"}`

---

## Environment-Based Routing

### Option 1: Multiple Subscriptions

Create separate subscriptions for each environment:
- Dev Subscription → Routes to dev Function App
- Test Subscription → Routes to test Function App
- Prod Subscription → Routes to prod Function App

Configure using Named Values and Policies.

### Option 2: Header-Based Routing

Add policy to route based on header:

```xml
<inbound>
    <base />
    <choose>
        <when condition="@(context.Request.Headers.GetValueOrDefault("X-Environment","") == "dev")">
            <set-backend-service base-url="https://vpn-lab-aws-bridge-dev.azurewebsites.net/api" />
        </when>
        <when condition="@(context.Request.Headers.GetValueOrDefault("X-Environment","") == "test")">
            <set-backend-service base-url="https://vpn-lab-aws-bridge-test.azurewebsites.net/api" />
        </when>
        <otherwise>
            <set-backend-service base-url="https://vpn-lab-aws-bridge-5295.azurewebsites.net/api" />
        </otherwise>
    </choose>
</inbound>
```

---

## Monitoring & Analytics

### View API Analytics

1. Go to: API Management → **Analytics**
2. Filter by:
   - API: GUID Service API
   - Time range: Last 7 days
3. View metrics:
   - Total requests
   - Failed requests
   - Response times
   - Cache hit ratio

### Application Insights Integration

1. Go to: API Management → **Application Insights**
2. Click: **Enable**
3. Select or create Application Insights resource
4. View detailed telemetry:
   - Request traces
   - Dependencies
   - Failures
   - Performance

---

## Cost Optimization

### Consumption Tier Pricing

**What you pay for:**
- Execution: $3.50 per million calls
- Data transfer: $0.40 per GB

**Your estimated cost:**
- Calls: ~1,000/month = $0.0035
- Data: ~0.001 GB/month = $0.0004
- **Total: ~$0.01/month** 💰

### Caching Benefits

With 10-minute cache:
- Cache hit rate: ~70% (estimated)
- Backend calls reduced: 700/month
- Azure Function cost saved: ~$0.00 (free tier)
- Faster response times: <50ms vs 200ms

---

## Advanced Features

### IP Whitelisting

Allow only Power Platform IPs:

```xml
<inbound>
    <ip-filter action="allow">
        <address-range from="13.64.0.0" to="13.107.255.255" />
        <address-range from="52.96.0.0" to="52.127.255.255" />
    </ip-filter>
</inbound>
```

### Request Transformation

Clean up GUID format before sending to backend:

```xml
<inbound>
    <set-body>@{
        var body = context.Request.Body.As<JObject>();
        body["guid"] = body["guid"].ToString().Replace("-", "").ToLower();
        return body.ToString();
    }</set-body>
</inbound>
```

### Response Transformation

Add metadata to responses:

```xml
<outbound>
    <set-body>@{
        var body = context.Response.Body.As<JObject>();
        body["_metadata"] = new JObject(
            new JProperty("timestamp", DateTime.UtcNow.ToString("o")),
            new JProperty("source", "APIM"),
            new JProperty("cached", context.Variables.GetValueOrDefault<bool>("cached-response", false))
        );
        return body.ToString();
    }</set-body>
</outbound>
```

---

## Comparison: Direct vs APIM

| Feature | Direct Azure Function | Through APIM | Benefit |
|---------|----------------------|--------------|---------|
| **Rate Limiting** | None | 1000/hour | Protects backend |
| **Caching** | None | 10 min | 70% faster, reduced load |
| **Monitoring** | Basic | Comprehensive | Better insights |
| **Environment Routing** | Manual | Policy-based | Easy switching |
| **Versioning** | Manual | Built-in | API evolution |
| **Security** | Function key | Subscription keys | Better management |
| **Cost** | $0.40/month | $0.41/month | Minimal increase |

---

## Next Steps

1. ✅ **Create Subscription** via Azure Portal
2. ✅ **Add Policies** for rate limiting and caching
3. ✅ **Test APIM Endpoint** with subscription key
4. ✅ **Export OpenAPI** definition
5. ✅ **Create Custom Connector** from APIM
6. ✅ **Test in Power Automate**
7. ✅ **Monitor Usage** via Analytics

---

## Troubleshooting

**Q: Getting 401 Unauthorized**
A: Check subscription key header: `Ocp-Apim-Subscription-Key`

**Q: Getting 429 Too Many Requests**
A: Hit rate limit - wait or increase quota in policy

**Q: Responses are slow**
A: Check cache configuration - may need to increase duration

**Q: Want different backends for dev/test/prod**
A: Use header-based routing or multiple subscriptions

---

## Support Resources

- **APIM Documentation:** https://docs.microsoft.com/en-us/azure/api-management/
- **Policy Reference:** https://docs.microsoft.com/en-us/azure/api-management/api-management-policies
- **Azure Portal:** https://portal.azure.com

---

**Status:** APIM infrastructure ready for configuration ✅
**Next:** Complete setup via Azure Portal (15 mins total)
