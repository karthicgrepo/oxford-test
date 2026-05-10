"""Access token endpoints.

Only listing is supported via this proxy. Generating a new token requires a
browser/SSO-authenticated session against the upstream API; see the
"Authentication" section of the README.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import TokenServiceDep
from app.schemas.token import AccessToken

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get(
    "",
    response_model=list[AccessToken],
    response_model_by_alias=False,
    summary="List active Oxford Economics access tokens for the current user",
)
async def list_tokens(service: TokenServiceDep) -> list[AccessToken]:
    return await service.list_tokens()
