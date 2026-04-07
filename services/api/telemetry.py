"""Structured request logging for the SnapBack API."""

from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import Request, Response

logger = logging.getLogger("snapback.request")


async def telemetry_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    response: Response | None = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as error:
        logger.exception(
            json.dumps(
                {
                    "event": "request_failed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "principal_id": getattr(getattr(request.state, "principal", None), "principal_id", "anonymous"),
                    "error": str(error),
                },
                sort_keys=True,
            )
        )
        raise
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        principal_id = getattr(getattr(request.state, "principal", None), "principal_id", "anonymous")
        logger.info(
            json.dumps(
                {
                    "event": "request_completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "principal_id": principal_id,
                },
                sort_keys=True,
            )
        )
        if response is not None:
            response.headers["X-Request-ID"] = request_id
