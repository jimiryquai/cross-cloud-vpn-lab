# Quick Reference Card - GUID Service

## One-Page Cheat Sheet

### Architecture
```
Power Platform → APIM → Azure Function → AWS (Secrets + Cognito + API) → Response
```

### URLs
| Component | URL |
|-----------|-----|
| APIM | `https://vpn-lab-apim-guid.azure-api.net/guid/GetGUID` |
| Function | `https://vpn-lab-aws-bridge-5295.azurewebsites.net/api/GetGUID` |
| AWS API | `https://z3euh2qc03.execute-api.eu-west-2.amazonaws.com/test/nino/{guid}` |

### Authentication
| Layer | Type | Location |
|-------|------|----------|
| Power Platform → APIM | Subscription Key | Header: `Ocp-Apim-Subscription-Key` |
| APIM → Function | Function Key | Query: `?code=...` (added by policy) |
| Function → AWS | IAM | App Settings (encrypted) |
| Function → Cognito | OAuth | Client Credentials (from Secrets Manager) |
| Function → API | Bearer | OAuth token (cached 59 min) |

### Keys (All in Azure Key Vault)
```
APIM Subscription: azure-apim-subscription-key
Function Key: azure-function-key
```

### Request/Response
```bash
# Request
POST https://vpn-lab-apim-guid.azure-api.net/guid/GetGUID
Ocp-Apim-Subscription-Key: YOUR_KEY
{"guid": "123e4567-e89b-12d3-a456-426614174000"}

# Response
{"nino": "AB123456C", "firstName": "John", "lastName": "Doe", ...}
```

### Troubleshooting
| Error | Fix |
|-------|-----|
| 401 | Check subscription key |
| 429 | Hit rate limit (1000/hour) |
| 500 | Check Function logs |
| Slow | First call = 2-3s (cold start), subsequent <500ms |

### Cost
```
AWS Secrets:  $0.40/month
APIM:         $0.01/month
Function:     $0.00/month (free tier)
TOTAL:        $0.41/month
```

### Performance
```
Cold start:        2-3 seconds
With token cache:  200-500ms
APIM cache hit:    <50ms
```

### Debug Commands
```bash
# Get subscription key
az rest --method post \
  --uri "/subscriptions/.../power-platform-sub/listSecrets?api-version=2021-08-01"

# Function logs
az functionapp log tail --name vpn-lab-aws-bridge-5295 -g vpn-lab-rg

# Test directly
curl -X POST https://vpn-lab-aws-bridge-5295.azurewebsites.net/api/GetGUID?code=KEY \
  -d '{"guid":"123e4567-e89b-12d3-a456-426614174000"}'
```

### Power Platform Usage
```javascript
// Power Automate: Get Person Details action
// Output: nino, firstName, lastName

// Power Apps
Set(Person, GUIDServiceConnector.GetPersonDetails({guid: GuidValue}))
Label.Text = Person.nino
```
