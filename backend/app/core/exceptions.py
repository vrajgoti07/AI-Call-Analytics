"""
AI Call Analytics — Application Exceptions & Global Exception Handlers.
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("backend.app.core.exceptions")


class AppException(Exception):
    """Base application exception for controlled API error handling."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class CallNotFoundError(AppException):
    def __init__(self, call_id: Any) -> None:
        super().__init__(
            code="CALL_NOT_FOUND",
            message=f"Call record '{call_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class JobNotFoundError(AppException):
    def __init__(self, job_id: Any) -> None:
        super().__init__(
            code="JOB_NOT_FOUND",
            message=f"Processing job '{job_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class AudioUploadError(AppException):
    def __init__(self, message: str, code: str = "INVALID_AUDIO_UPLOAD") -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class AudioTooLargeError(AppException):
    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            code="AUDIO_TOO_LARGE",
            message=f"Audio file size ({size_bytes} bytes) exceeds limit ({max_bytes} bytes).",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class UnsupportedAudioError(AppException):
    def __init__(self, extension: str) -> None:
        super().__init__(
            code="UNSUPPORTED_AUDIO",
            message=f"Audio extension '{extension}' is not supported.",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


class TranscriptionFailedError(AppException):
    def __init__(self, message: str = "Transcription could not be completed.") -> None:
        super().__init__(
            code="TRANSCRIPTION_FAILED",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class DiarizationFailedError(AppException):
    def __init__(self, message: str = "Speaker diarization could not be completed.") -> None:
        super().__init__(
            code="DIARIZATION_FAILED",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class AuthenticationError(AppException):
    def __init__(self, message: str = "Invalid credentials or authentication token.") -> None:
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class CompanyNotFoundError(AppException):
    def __init__(self, company_id: Any) -> None:
        super().__init__(
            code="COMPANY_NOT_FOUND",
            message=f"Company '{company_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform global exception handlers on the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "AppException: code=%s message=%s status=%d request_id=%s",
            exc.code,
            exc.message,
            exc.status_code,
            request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        errors = [
            {"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")}
            for err in exc.errors()
        ]
        logger.info(
            "Validation error on %s %s request_id=%s errors=%s",
            request.method,
            request.url.path,
            request_id,
            errors,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request payload or parameters validation failed.",
                    "request_id": request_id,
                    "details": errors,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        code_map = {
            404: "NOT_FOUND",
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            405: "METHOD_NOT_ALLOWED",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": str(exc.detail),
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "Unhandled server exception on %s %s request_id=%s: %s",
            request.method,
            request.url.path,
            request_id,
            str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please contact system administrator.",
                    "request_id": request_id,
                }
            },
        )
