"""Business logic for solve operations."""

from __future__ import annotations

import logging

from app.clients.oxford_client import OxfordEconomicsClient
from app.schemas.solve import SolveOperation, SolveRequest

logger = logging.getLogger(__name__)


class SolveService:
    """Coordinates solve requests against the Oxford Economics API."""

    def __init__(self, client: OxfordEconomicsClient) -> None:
        self._client = client

    async def trigger_solve(self, request: SolveRequest) -> SolveOperation:
        logger.info(
            "Triggering solve: input=%s output=%s range=%s..%s wait=%s",
            request.input_forecast,
            request.output_forecast,
            request.solution_range.from_period,
            request.solution_range.to_period,
            request.wait_for_completion,
        )
        operation = await self._client.trigger_solve(request.to_upstream_payload())
        logger.info("Solve queued id=%s status=%s", operation.id, operation.status)

        if request.wait_for_completion and not operation.is_terminal:
            operation = await self._client.await_operation(operation.id)
            logger.info("Solve terminal id=%s status=%s", operation.id, operation.status)

        return operation

    async def get_operation(self, operation_id: str) -> SolveOperation:
        return await self._client.get_operation(operation_id)
