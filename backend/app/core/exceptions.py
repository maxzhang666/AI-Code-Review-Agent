from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: int = 400
    default_message: str = "Application error"

    def __init__(
        self,
        message: str | None = None,
        *,
        errors: Any = None,
        code: int | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.errors = errors
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = 404
    default_message = "Resource not found"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = 401
    default_message = "Unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = 403
    default_message = "Forbidden"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = 409
    default_message = "Conflict"


def _error_body(code: int, message: str, errors: Any = None) -> dict:
    return {"code": code, "message": message, "errors": errors}


async def _handle_app_error(_req: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.errors),
    )


async def _handle_http_exception(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.status_code, str(exc.detail)),
    )


async def _handle_validation_error(_req: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(422, "Validation error", exc.errors()),
    )


async def _handle_unhandled(req: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(req.state, "request_id", None)
    logging.getLogger(__name__).exception(
        "unhandled_exception request_id=%s method=%s path=%s",
        request_id, req.method, req.url.path,
    )
    return JSONResponse(
        status_code=500,
        content=_error_body(
            500, "Internal server error",
            {"request_id": request_id} if request_id else None,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unhandled)
