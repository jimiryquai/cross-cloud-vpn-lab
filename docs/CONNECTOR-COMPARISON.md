# Power Platform Custom Connectors

Two custom connectors for AtW GUID Service integration, exported from Power Platform solution.

---

## Connectors

### 1. `jr_getnino` - Direct to Azure Function
**Architecture**: Power Platform → Azure Function → AWS

- **Host**: `vpn-lab-aws-bridge-5295.azurewebsites.net`
- **Base Path**: `/api`
- **Authentication**: API Key (query parameter `code` = Azure Function key)
- **Use When**: Simplicity preferred, AWS rate limiting sufficient

**Pros**:
- ✅ Simpler architecture (one less hop)
- ✅ Faster (~100-200ms improvement)
- ✅ Lower cost (no APIM)
- ✅ Fewer dependencies

**Cons**:
- ⚠️ No APIM caching
- ⚠️ No client-side rate limiting
- ⚠️ No APIM analytics

---

### 2. `new_5Fguid-20service-20api` - Via Azure API Management
**Architecture**: Power Platform → APIM → Azure Function → AWS

- **Host**: `vpn-lab-apim-guid.azure-api.net`
- **Base Path**: `/guid`
- **Authentication**: API Key (header `Ocp-Apim-Subscription-Key` = APIM subscription key)
- **Use When**: Enterprise features required (rate limiting, caching, monitoring)

**Pros**:
- ✅ Rate limiting (1000/hour per subscription)
- ✅ Response caching (10 minutes)
- ✅ APIM analytics and monitoring
- ✅ Environment-based routing via policies

**Cons**:
- ⚠️ Extra network hop (+50ms latency)
- ⚠️ Slightly higher cost (+$0.01/month)
- ⚠️ More complex configuration

---

## Solution Structure

```
power-platform/solution/
├── Connectors/
│   ├── jr_getnino_*                          # Direct connector files
│   └── new_5Fguid-20service-20api_*          # APIM connector files
├── Other/
│   ├── Customizations.xml
│   └── Solution.xml
└── [Content_Types].xml
```

---

## Importing to Power Platform

### Option 1: Import Packed Solution (Recommended)

```bash
# Pack solution
pac solution pack \
  --zipfile ./GUIDServiceConnectors.zip \
  --folder ./power-platform/solution

# Import to target environment
pac solution import \
  --path ./GUIDServiceConnectors.zip \
  --activate-plugins
```

### Option 2: Import Individual Connectors

1. Go to Power Platform → Custom Connectors
2. New custom connector → Import an OpenAPI file
3. Upload `*_openapidefinition.json`
4. Configure connection parameters from `*_connectionparameters.json`

---

## Files Explained

Each connector has these files:

| File | Purpose |
|------|---------|
| `*_openapidefinition.json` | Swagger/OpenAPI definition (API structure) |
| `*_connectionparameters.json` | Connection authentication configuration |
| `*_policytemplateinstances.json` | Power Platform policies (if any) |

---

## Testing

### Test GUID
```
123e4567-e89b-12d3-a456-426614174000
```

### Expected Response
```json
{
  "nino": "AB123456C",
  "firstName": "John",
  "lastName": "Doe",
  "guid": "123e4567-e89b-12d3-a456-426614174000"
}
```

---

## Which Connector Should You Use?

### Choose Direct (`jr_getnino`) if:
- You want simplest architecture
- AWS API Gateway rate limiting is sufficient
- Minimizing latency is priority
- Lower operational complexity preferred

### Choose APIM (`new_5Fguid-20service-20api`) if:
- Need enterprise monitoring/analytics
- Want client-side rate limiting (on top of AWS)
- Response caching desired for performance
- Environment routing through policies needed
- Centralized API management required

---

## Architect Recommendation

Based on feedback: **AWS handles rate limiting, so Direct connector may be sufficient**. APIM adds value for:
- Response caching (10 min) for repeated GUIDs
- Centralized monitoring across multiple APIs
- Environment-based routing without code changes

**For most use cases**: Start with **Direct connector** for simplicity, add APIM later if needed.

---

## Deployment Checklist

### For Direct Connector (`jr_getnino`)
- [ ] Azure Function deployed and running
- [ ] Function key stored in Azure Key Vault
- [ ] Power Platform Environment Variable created
- [ ] Connection created in Power Platform
- [ ] Test with sample GUID

### For APIM Connector (`new_5Fguid-20service-20api`)
- [ ] Azure APIM instance deployed
- [ ] APIM policy configured (see `/docs/APIM-SETUP.md`)
- [ ] APIM subscription created for Power Platform
- [ ] Subscription key stored in Azure Key Vault
- [ ] Power Platform Environment Variable created
- [ ] Connection created in Power Platform
- [ ] Test with sample GUID

---

## Performance Comparison

| Metric | Direct | via APIM |
|--------|--------|----------|
| Cold start | 2-3s | 2-3s |
| Warm (no cache) | 200-500ms | 250-550ms |
| Warm (APIM cache hit) | N/A | <50ms |
| Network hops | 1 | 2 |

---

**Last Updated**: 2025-01-11
**Solution Version**: 1.0.0
