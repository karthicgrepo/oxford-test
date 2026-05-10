"""Business logic for access tokens (listing only).

Token generation is not supported via Bearer auth — see the upstream API note
in `app/schemas/token.py`.
"""

from __future__ import annotations

from app.clients.oxford_client import OxfordEconomicsClient
from app.schemas.token import AccessToken


class TokenService:
    def __init__(self, client: OxfordEconomicsClient) -> None:
        self._client = client

    async def list_tokens(self) -> list[AccessToken]:
        return await self._client.list_access_tokens()
