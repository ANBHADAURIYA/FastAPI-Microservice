"""Domain exceptions and the handlers that turn them into HTTP responses.

Services raise meaningful exceptions (CityNotFoundError, UpstreamError, ...)
and know nothing about HTTP. The handlers registered here map them to status
codes, so every error leaves the API in the same JSON shape:

    {"error": {"code": "city_not_found", "message": "..."}, "request_id": "..."}
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    message = "Internal server error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message


class CityNotFoundError(AppError):
    status_code = 404
    code = "city_not_found"
    message = "City not found"


class UpstreamError(AppError):
    """An external API (weather, joke) failed."""

    status_code = 502
    code = "upstream_error"
    message = "Upstream service failed"


class LLMError(AppError):
    status_code = 502
    code = "llm_error"
    message = "Summary generation failed"


class InvalidTextError(AppError):
    status_code = 400
    code = "invalid_text"
    message = "Invalid text"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Missing or invalid API key"


def _error_response(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}, "request_id": request_id_ctx.get()},
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "ApiKey"} if exc.status_code == 401 else None
        return _error_response(exc.status_code, exc.code, exc.message, headers)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first["loc"])
        message = f"{field}: {first['msg']}"
        # The assignment requires 400 (not FastAPI's default 422) for a bad
        # JSON body on /summary. Query-parameter errors stay 422.
        status = 400 if first["loc"] and first["loc"][0] == "body" else 422
        return _error_response(status, "invalid_request", message)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _error_response(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return _error_response(429, "rate_limited", "Too many requests, slow down")

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the traceback server-side; never leak it to the client.
        logger.exception("Unhandled error")
        return _error_response(500, "internal_error", "Internal server error")
