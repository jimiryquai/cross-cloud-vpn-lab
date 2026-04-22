import json
from functools import wraps
from shared.auth.arn import get_project_arn
from shared.context_logger import ContextLogger
import azure.functions as func
from pydantic import ValidationError

logger = ContextLogger()

def project_context_middleware(handler):
    @wraps(handler)
    def wrapper(req, *args, **kwargs):
        # Validate project param
        project = req.params.get("project")
        if not project:
            return func.HttpResponse(
                json.dumps({"error": "Missing required query parameter: project"}),
                status_code=400,
                mimetype="application/json",
            )
        correlation_id = req.headers.get("correlation-id", "not-provided")
        try:
            arn = get_project_arn(project)
        except ValidationError as ve:
            logger.error(f"Project ARN validation failed: {ve}", project=project, correlation_id=correlation_id)
            return func.HttpResponse(
                json.dumps({"error": ve.errors()}),
                status_code=400,
                mimetype="application/json",
            )
        except Exception as e:
            logger.error(f"Project ARN error: {e}", project=project, correlation_id=correlation_id)
            return func.HttpResponse(
                json.dumps({"error": str(e)}),
                status_code=500,
                mimetype="application/json",
            )
        # Attach context for downstream use
        req.context = {"project": project, "correlation_id": correlation_id, "arn": arn}
        logger.info("Project context validated.", project=project, correlation_id=correlation_id)
        return handler(req, *args, **kwargs)
    return wrapper
