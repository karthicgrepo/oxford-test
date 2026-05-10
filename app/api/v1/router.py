"""Aggregates all v1 routers under a single APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import health, solve, token

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(solve.router)
api_router.include_router(token.router)
