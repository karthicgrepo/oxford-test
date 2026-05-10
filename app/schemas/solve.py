"""Pydantic models for the GMWO ``/v1/operations/solve`` endpoint.

Field aliases match the upstream Oxford Economics API (PascalCase) exactly as
defined in the GMWO swagger (``SolveForecast`` and ``ForecastOperation``);
Python attributes use snake_case for idiomatic FastAPI usage.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _ApiModel(BaseModel):
    """Base model that round-trips the upstream PascalCase contract."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )


class PeriodRange(_ApiModel):
    """A from/to period range, e.g. 2023Q2 -> 2027Q4."""

    from_period: str = Field(
        ...,
        alias="From",
        min_length=1,
        examples=["2023Q2"],
        description="Inclusive start period (e.g. '2023Q2', '2024M01').",
    )
    to_period: str = Field(
        ...,
        alias="To",
        min_length=1,
        examples=["2027Q4"],
        description="Inclusive end period.",
    )


class OperationStatus(StrEnum):
    """Mirrors the upstream OperationStatus enum."""

    QUEUED = "Queued"
    IN_PROGRESS = "InProgress"
    FAILED = "Failed"
    SUCCEEDED = "Succeeded"
    CANCELLED = "Cancelled"


class OperationResourceRole(StrEnum):
    INPUT = "Input"
    OUTPUT = "Output"


class SolveRequest(_ApiModel):
    """Request body for triggering a model solve.

    Mirrors the upstream `SolveForecast` schema (= `ApplyForecastBase` + the
    solve-specific `SolutionRange` and `Groups`). `Commands` and `CommandsFile`
    are mutually exclusive; omit both to solve without changes.
    """

    input_forecast: str = Field(
        ...,
        alias="InputForecast",
        min_length=1,
        description="Path to the source forecast.",
    )
    output_forecast: str = Field(
        ...,
        alias="OutputForecast",
        min_length=1,
        description="Path where the solved forecast will be written.",
    )
    solution_range: PeriodRange = Field(..., alias="SolutionRange")
    operation_name: str | None = Field(default=None, alias="OperationName")
    commands: str | None = Field(
        default=None,
        alias="Commands",
        description="Inline 3FS commands. Mutually exclusive with commands_file.",
    )
    commands_file: str | None = Field(
        default=None,
        alias="CommandsFile",
        description="Path to a stored commands file or import workbook.",
    )
    groups: list[str] | None = Field(default=None, alias="Groups")

    wait_for_completion: bool = Field(
        default=False,
        description=(
            "If true, the service polls the upstream /operations/{id}/await "
            "endpoint until the operation reaches a terminal state before returning."
        ),
    )

    def to_upstream_payload(self) -> dict[str, Any]:
        """Serialise to the exact PascalCase payload expected upstream."""
        return self.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude={"wait_for_completion"},
        )


class ForecastArtifact(_ApiModel):
    id: str = Field(..., alias="Id")
    filename: str = Field(..., alias="Filename")
    type: str = Field(..., alias="Type")
    download_url: str = Field(..., alias="DownloadUrl")


class OperationResource(_ApiModel):
    id: str = Field(..., alias="Id")
    path: str | None = Field(default=None, alias="Path")
    version: int = Field(..., alias="Version")
    role: OperationResourceRole = Field(..., alias="Role")


class SolveOperation(_ApiModel):
    """Response from the upstream solve / await endpoints (`ForecastOperation`)."""

    id: str = Field(..., alias="Id")
    status: OperationStatus = Field(..., alias="Status")
    name: str | None = Field(default=None, alias="Name")
    created_at: datetime = Field(..., alias="CreatedAt")
    started_at: datetime | None = Field(default=None, alias="StartedAt")
    completed_at: datetime | None = Field(default=None, alias="CompletedAt")
    duration: int | None = Field(
        default=None,
        alias="Duration",
        description="Operation duration in seconds (upstream int32).",
    )
    failure_reason: str | None = Field(default=None, alias="FailureReason")
    artifacts: list[ForecastArtifact] = Field(default_factory=list, alias="Artifacts")
    resources: list[OperationResource] = Field(default_factory=list, alias="Resources")

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            OperationStatus.SUCCEEDED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        }
