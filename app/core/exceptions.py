"""Application-level exceptions and FastAPI exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class OxfordAPIError(Exception):
    """Raised when the upstream Oxford Economics API returns an error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        upstream_status: int | None = None,
        upstream_body: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.upstream_status = upstream_status
        self.upstream_body = upstream_body


class OxfordAPIAuthError(OxfordAPIError):
    """Raised when authentication against the Oxford Economics API fails."""

    def __init__(self, message: str = "Oxford Economics authentication failed") -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class OxfordAPITimeoutError(OxfordAPIError):
    """Raised when the upstream call exceeds the configured timeout."""

    def __init__(self, message: str = "Oxford Economics request timed out") -> None:
        super().__init__(message, status_code=status.HTTP_504_GATEWAY_TIMEOUT)


def register_exception_handlers(app: FastAPI) -> None:
    """Wire up handlers that translate domain exceptions to HTTP responses."""

    @app.exception_handler(OxfordAPIError)
    async def _oxford_api_error_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: OxfordAPIError
    ) -> JSONResponse:
        logger.warning(
            "Oxford API error path=%s status=%s upstream=%s detail=%s",
            request.url.path,
            exc.status_code,
            exc.upstream_status,
            exc.message,
        )
        payload: dict[str, Any] = {"detail": exc.message}
        if exc.upstream_status is not None:
            payload["upstream_status"] = exc.upstream_status
        if exc.upstream_body is not None:
            payload["upstream_body"] = exc.upstream_body
        return JSONResponse(status_code=exc.status_code, content=payload)
