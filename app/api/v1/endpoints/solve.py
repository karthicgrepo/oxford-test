"""Solve API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Path, status

from app.api.deps import SolveServiceDep
from app.schemas.solve import SolveOperation, SolveRequest

router = APIRouter(prefix="/solve", tags=["solve"])


@router.post(
    "",
    response_model=SolveOperation,
    response_model_by_alias=False,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger an Oxford Economics solve operation",
)
async def trigger_solve(
    request: SolveRequest,
    service: SolveServiceDep,
) -> SolveOperation:
    """Submit a solve request to the GMWO API.

    If ``wait_for_completion`` is true, the service polls the upstream
    ``/operations/{id}/await`` endpoint until the operation reaches a terminal
    state and returns the final operation; otherwise it returns immediately
    with status ``Queued`` or ``InProgress``.
    """
    return await service.trigger_solve(request)


@router.get(
    "/operations/{operation_id}",
    response_model=SolveOperation,
    response_model_by_alias=False,
    summary="Fetch the current state of a solve operation",
)
async def get_operation(
    service: SolveServiceDep,
    operation_id: str = Path(..., min_length=1, description="Operation Id returned by /solve."),
) -> SolveOperation:
    return await service.get_operation(operation_id)
