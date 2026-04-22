# Code Quality Improvement Plan

This plan tracks actionable improvements for enterprise, multi-tenant, and testability alignment in the cross-cloud-vpn-lab codebase. Each item is mapped to a recommendation from the recent code review.

## 1. Project ARN Caching
- [x] Implement an in-memory cache for ARNs in shared/auth.py
- [x] Add tests for ARN caching logic

## 2. Structured Logging
- [x] Ensure all logs include tenant/project and correlation ID.
- [x] Refactor logging statements to always include project and correlation ID context.
- [x] Add ContextLogger helper for consistent context. See docs/structured-logging.md for usage.

## 3. Input Validation
- [x] Validate all incoming request parameters and payloads.
- [x] Add schema validation for all API inputs (using pydantic).
- [x] Return clear error messages for invalid payloads.

## 4. Dependency Injection & Modularity
- [x] Refactor for better testability and extensibility.
- [x] Decouple external dependencies (Key Vault, Cognito, requests) via dependency injection.
- [x] Split shared/auth.py into smaller modules (token, secret, arn logic).

## 5. Expanded Unit Tests
- [x] Cover secret caching, error paths, and logging with unit tests.
- [x] Add tests for secret caching logic.
- [x] Add tests for error handling and logging.
- [x] Use parameterized tests for expiration logic.

## 6. Middleware for Common Logic
- **Goal:** Centralize project validation and logging context.
- **Status:** Middleware and tests implemented, pydantic v2 compatibility resolved. All tests pass.
- **Actions:**
  - Implement a middleware/decorator for project ARN validation and context logging. **[done]**
  - Remove duplicate code from route handlers. **[done]**
  - Update test to resolve pydantic v2 ValidationError handling. **[done]**

## 7. Environment Variable Documentation & Validation
- **Goal:** Document and validate all required environment variables at startup.
- **Actions:**
  - Add a startup check for required environment variables.
  - Document all required variables in README and code comments.

---

**Status:** Draft (to be updated as improvements are implemented)
