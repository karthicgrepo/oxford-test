"""FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request

from app.clients.oxford_client import OxfordEconomicsClient
from app.core.config import Settings, get_settings
from app.services.solve_service import SolveService
from app.services.token_service import TokenService


def get_app_settings() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


async def get_oxford_client(request: Request) -> AsyncIterator[OxfordEconomicsClient]:
    """Yield the application-scoped Oxford Economics client.

    The client is created once at startup (see ``app.main.lifespan``) and stored on
    ``app.state``; we expose it here so endpoints can declare it as a dependency.
    """
    client: OxfordEconomicsClient = request.app.state.oxford_client
    yield client


OxfordClientDep = Annotated[OxfordEconomicsClient, Depends(get_oxford_client)]


def get_solve_service(client: OxfordClientDep) -> SolveService:
    return SolveService(client)


SolveServiceDep = Annotated[SolveService, Depends(get_solve_service)]


def get_token_service(client: OxfordClientDep) -> TokenService:
    return TokenService(client)


TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]
