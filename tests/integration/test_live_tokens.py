"""Live tests for the token endpoints.

Run with::

    pytest -m "live and tokens"

Note: `POST /v1/access-token/generate` upstream is *not* callable via Bearer
auth (it returns ``400 Cannot create access token unless authenticated as a
user.``), so this proxy only exposes listing. To mint a new token, use the
Swagger UI at https://model.oxfordeconomics.com/api/v1/swagger in a logged-in
browser session.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.live, pytest.mark.tokens]


async def test_list_tokens(client: AsyncClient) -> None:
    """GET /api/v1/tokens — lists all active tokens for the caller."""
    response = await client.get("/api/v1/tokens")
    assert response.status_code == 200, response.text

    tokens = response.json()
    assert isinstance(tokens, list)
    assert tokens, "Expected at least one active token (the one configured in .env)"

    print("\nActive Oxford Economics access tokens:")
    for t in tokens:
        print(f"  {t['id']}  {str(t['created_at'])[:19]}  {t['name']!r}")

    for t in tokens:
        assert t["id"] and t["name"] and t["created_at"]
