"""Async HTTP client for the Oxford Economics GMWO API.

Encapsulates Bearer authentication, retries on transient failures,
and consistent error translation into domain exceptions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Self

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings
from app.core.exceptions import (
    OxfordAPIAuthError,
    OxfordAPIError,
    OxfordAPITimeoutError,
)
from app.schemas.solve import SolveOperation
from app.schemas.token import AccessToken

logger = logging.getLogger(__name__)

_TERMINAL_POLL_INTERVAL_SECONDS = 2.0
_MAX_POLL_ITERATIONS = 1800  # safety cap (~1h at 2s)


class OxfordEconomicsClient:
    """Thin async wrapper over httpx for the Oxford Economics API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.oe_api_base_url_str,
            timeout=httpx.Timeout(settings.oe_api_timeout_seconds),
            headers={
                "Authorization": f"Bearer {settings.oe_api_token.get_secret_value()}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ----- public API -----

    async def trigger_solve(self, payload: dict[str, Any]) -> SolveOperation:
        """POST /v1/operations/solve."""
        data = await self._request("POST", "/v1/operations/solve", json=payload)
        return SolveOperation.model_validate(data)

    async def get_operation(self, operation_id: str) -> SolveOperation:
        """GET /v1/operations/{id} (non-blocking status fetch)."""
        data = await self._request("GET", f"/v1/operations/{operation_id}")
        return SolveOperation.model_validate(data)

    async def await_operation(self, operation_id: str) -> SolveOperation:
        """Poll /v1/operations/{id}/await until the operation is terminal."""
        for _ in range(_MAX_POLL_ITERATIONS):
            data = await self._request("GET", f"/v1/operations/{operation_id}/await")
            op = SolveOperation.model_validate(data)
            if op.is_terminal:
                return op
            await asyncio.sleep(_TERMINAL_POLL_INTERVAL_SECONDS)
        raise OxfordAPIError(
            f"Operation {operation_id} did not reach a terminal state within the polling window."
        )

    async def list_access_tokens(self) -> list[AccessToken]:
        """GET /v1/access-token (lists all active tokens for the current user)."""
        data = await self._request("GET", "/v1/access-token")
        return [AccessToken.model_validate(item) for item in (data or [])]

    # ----- internals -----

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Perform an HTTP request with retry on transient errors."""
        attempts = max(1, self._settings.oe_api_max_retries)
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(attempts),
                wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
                retry=retry_if_exception_type(
                    (httpx.TransportError, httpx.RemoteProtocolError)
                ),
                reraise=True,
            ):
                with attempt:
                    response = await self._client.request(
                        method, path, json=json, params=params
                    )
                    return self._handle_response(response)
        except httpx.TimeoutException as exc:
            logger.warning("Oxford API timeout method=%s path=%s", method, path)
            raise OxfordAPITimeoutError() from exc
        except httpx.HTTPError as exc:
            logger.exception("Oxford API transport error method=%s path=%s", method, path)
            raise OxfordAPIError(f"Transport error contacting Oxford Economics: {exc}") from exc

        # Should never reach here -- AsyncRetrying always yields at least once.
        raise OxfordAPIError("Unknown error contacting Oxford Economics API.")

    @staticmethod
    def _handle_response(response: httpx.Response) -> Any:
        if response.is_success:
            if not response.content:
                return None
            return response.json()

        body: Any
        try:
            body = response.json()
        except ValueError:
            body = response.text

        if response.status_code == 401:
            raise OxfordAPIAuthError()
        raise OxfordAPIError(
            f"Oxford Economics API returned HTTP {response.status_code}",
            upstream_status=response.status_code,
            upstream_body=body,
        )
