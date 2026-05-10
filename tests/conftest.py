"""Shared pytest fixtures.

Tests marked with ``@pytest.mark.live`` use the real ``.env`` (and therefore
the real Oxford Economics API). All other tests get a deterministic fake
token so they run offline.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _env(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Provide deterministic settings for the test process.

    For ``live``-marked tests, leave the real ``.env`` in place so the service
    talks to the real upstream. For everything else, override with a fake
    token so unit tests are fully offline.
    """
    is_live = "live" in request.keywords
    if not is_live:
        monkeypatch.setenv("OE_API_TOKEN", "test-token")
        monkeypatch.setenv("OE_API_BASE_URL", "https://model.oxfordeconomics.com/api")
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """ASGI test client driving the real FastAPI app (incl. lifespan).

    Used by both unit and live tests — the only difference is which token the
    underlying ``OxfordEconomicsClient`` was constructed with (see ``_env``).
    """
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as ac:
        async with app.router.lifespan_context(app):
            yield ac
