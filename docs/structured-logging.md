# Structured Logging with ContextLogger

This project uses a custom `ContextLogger` to ensure all logs include the `project` and `correlation_id` context for every request. This approach supports traceability and multi-tenant diagnostics.

## Usage

Import and instantiate the logger:

```python
from shared.context_logger import ContextLogger
logger = ContextLogger()
```

Replace standard logging calls with:

```python
logger.info("Message", project=project, correlation_id=correlation_id)
logger.error("Error message", project=project, correlation_id=correlation_id)
```

- `project` should be the current tenant/project identifier (from request params or headers).
- `correlation_id` should be the request's correlation ID (from headers or generated if missing).

## Example Output

```
[project=fqm] [correlation_id=abc123] Processing single GUID lookup.
[project=acs] [correlation_id=xyz789] Proxy Failure: Upstream service returned 500
```

## Why Structured Logging?
- Enables filtering and searching logs by project or correlation ID.
- Supports distributed tracing and debugging in multi-tenant environments.
- Ensures all logs are actionable and traceable to a specific request and tenant.

## Where to Use
- All API route handlers
- Shared modules (e.g., authentication, error handling)
- Any place where logs are emitted for requests or background jobs

## Implementation Details
- See `src/shared/context_logger.py` for implementation.
- All previous `logging.info`, `logging.error`, etc. should be replaced with the context logger for consistency.
