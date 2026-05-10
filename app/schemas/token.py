"""Pydantic models for the GMWO ``/v1/access-token`` endpoints.

Note: only `GET /v1/access-token` (list) is callable via Bearer auth. The
`POST /v1/access-token/generate` endpoint upstream rejects Bearer-authed
callers with HTTP 400 ("Cannot create access token unless authenticated as a
user.") — token generation must be done in a browser session via the Swagger
UI at https://model.oxfordeconomics.com/api/v1/swagger.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _ApiModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )


class AccessToken(_ApiModel):
    """Metadata for an existing access token (response from `GET /v1/access-token`)."""

    id: UUID = Field(..., alias="Id")
    name: str = Field(..., alias="Name")
    created_at: datetime = Field(..., alias="CreatedAt")
