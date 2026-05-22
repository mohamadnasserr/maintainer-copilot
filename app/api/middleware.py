import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.infra.redaction import redact_for_log

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        trace_id = request.headers.get("x-trace-id") or str(uuid4())

        request.state.request_id = request_id
        request.state.trace_id = trace_id

        start = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - start) * 1000, 2)

            logger.exception(
                redact_for_log(
                    {
                        "event": "request_failed",
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                    }
                ),
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                },
            )
            raise

        duration_ms = round((perf_counter() - start) * 1000, 2)

        response.headers["x-request-id"] = request_id
        response.headers["x-trace-id"] = trace_id

        logger.info(
            redact_for_log(
                {
                    "event": "request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            ),
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
            },
        )

        return response