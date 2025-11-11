# Cross-Cloud OAuth Integration - Lab Environment

Lab replication of client's AWS-based GUID Service integration using Power Platform, Azure APIM, and Azure Function.

## Quick Start

### 📊 Quick Reference (2 mins)
- **[QUICK-REFERENCE-CARD.md](QUICK-REFERENCE-CARD.md)** - One-page cheat sheet

### 📘 Complete Setup Guide (10 mins)
- **[CROSS-CLOUD-OAUTH-GUIDE.md](CROSS-CLOUD-OAUTH-GUIDE.md)** - Full documentation with architecture diagrams

### 🔧 Component Guides
- **[APIM-SETUP.md](APIM-SETUP.md)** - Azure API Management configuration
- **[CONNECTOR-COMPARISON.md](CONNECTOR-COMPARISON.md)** - Direct vs APIM connector comparison
- **[TEST-STRATEGY.md](TEST-STRATEGY.md)** - Testing approach and implementation

## Architecture

```
Power Platform Custom Connector
  ↓ APIM Subscription Key
Azure API Management
  ↓ Rate limiting, caching, policies
Azure Function (Python)
  ↓ AWS IAM → Secrets Manager → Cognito OAuth
AWS API Gateway
  ↓ Bearer token authentication
Mock GUID API
```

## What This Provides for Handover

✅ **Custom Connector** - Power Platform connector definition ready for export
✅ **Azure Function Code** - Python-based OAuth orchestration bridge
✅ **OAuth Abstraction** - Complete client credentials flow handled server-side
✅ **Test Suite** - Unit and integration tests for all components
✅ **Production Pattern** - Replicates client's Kong EE OAuth flow
✅ **Documentation** - Setup guides and troubleshooting

## Components for Handover

### 1. Custom Connectors
- **Location**: `/power-platform/solution/Connectors/`
- **Two Approaches**:
  - `jr_getnino` - Direct to Azure Function
  - `new_5Fguid-20service-20api` - Via APIM
- **Clean OpenAPI**: `/power-platform/openapi-direct-function.json`

### 2. Azure Function
- **Location**: `/azure-function/GetGUID/`
- **Runtime**: Python 3.11
- **Features**: Complete OAuth orchestration (Secrets Manager → Cognito → GUID API)
- **Token Caching**: 59 minutes in-memory
- **Dependencies**: `requirements.txt` + `requirements-dev.txt`

### 3. APIM Policy
- **Location**: Documented in `APIM-SETUP.md`
- **Features**: Rate limiting, caching, Function key injection

### 4. Tests
- **Test Suite**: `/azure-function/tests/`
- **Strategy**: `TEST-STRATEGY.md` - Real integration tests (90%) + minimal unit tests (10%)
- **Results**: 13 passed tests (7 unit, 6 integration)
- **Setup**: See `/azure-function/tests/README.md`

---

**Documentation Version:** 1.0
**Last Updated:** 2025-11-06
**Status:** Production Ready ✅
