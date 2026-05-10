"""Fixtures for integration tests that hit the real Oxford Economics API.

These tests are opt-in (run via ``pytest -m live``) and use the real bearer
token from ``.env``.

Override defaults with environment variables:
- ``OE_TEST_INPUT_FORECAST`` — pin a specific input forecast path.
  Default: latest forecast under ``/oxford-economics/releases/gem``.
- ``OE_TEST_OUTPUT_PREFIX`` — prefix for output forecasts created by tests.
  Default: ``/me/api-test-solve``.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio

from app.core.config import get_settings


@pytest_asyncio.fixture
async def upstream() -> AsyncIterator[httpx.AsyncClient]:
    """Pre-authenticated httpx client straight to the Oxford Economics API.

    Used for read-only setup calls (e.g. discovering the latest GEM forecast)
    that the FastAPI service does not itself proxy.
    """
    settings = get_settings()
    async with httpx.AsyncClient(
        base_url=settings.oe_api_base_url_str,
        headers={
            "Authorization": f"Bearer {settings.oe_api_token.get_secret_value()}",
            "Accept": "application/json",
        },
        timeout=60.0,
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def latest_gem_forecast_path(upstream: httpx.AsyncClient) -> str:
    """Resolve a valid `InputForecast` path for solve tests.

    Uses ``OE_TEST_INPUT_FORECAST`` if set; otherwise calls
    ``/v1/resources/oxford-economics/releases/gem`` and picks the most recently
    published forecast.
    """
    pinned = os.environ.get("OE_TEST_INPUT_FORECAST")
    if pinned:
        return pinned

    response = await upstream.get("/v1/resources/oxford-economics/releases/gem")
    response.raise_for_status()
    payload = response.json()

    forecasts = [c for c in payload.get("Children", []) if c.get("Type") == "Forecast"]
    if not forecasts:
        pytest.skip("No GEM forecasts found in oxford-economics/releases/gem")

    forecasts.sort(
        key=lambda f: f["Versions"][-1]["CreatedAt"],
        reverse=True,
    )
    return forecasts[0]["Path"]


@pytest.fixture
def output_forecast_path() -> str:
    """A unique destination path under the user's home so runs don't collide."""
    prefix = os.environ.get("OE_TEST_OUTPUT_PREFIX", "/me/api-test-solve")
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{prefix}-{ts}"
