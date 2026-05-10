"""End-to-end tests for the solve endpoint with the upstream API mocked."""

from __future__ import annotations

import respx
from httpx import AsyncClient, Response

UPSTREAM = "https://model.oxfordeconomics.com/api"


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@respx.mock
async def test_trigger_solve_returns_queued_operation(client: AsyncClient) -> None:
    respx.post(f"{UPSTREAM}/v1/operations/solve").mock(
        return_value=Response(
            200,
            json={
                "Id": "op-123",
                "Status": "Queued",
                "CreatedAt": "2026-05-10T10:00:00Z",
                "Artifacts": [],
                "Resources": [],
            },
        )
    )

    payload = {
        "input_forecast": "/me/forecasts/source",
        "output_forecast": "/me/forecasts/new-forecast",
        "solution_range": {"from_period": "2023Q2", "to_period": "2027Q4"},
        "commands_file": "/me/commands/myfile",
    }
    response = await client.post("/api/v1/solve", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["id"] == "op-123"
    assert body["status"] == "Queued"


@respx.mock
async def test_trigger_solve_waits_for_completion(client: AsyncClient) -> None:
    respx.post(f"{UPSTREAM}/v1/operations/solve").mock(
        return_value=Response(
            200,
            json={
                "Id": "op-456",
                "Status": "Queued",
                "CreatedAt": "2026-05-10T10:00:00Z",
                "Artifacts": [],
                "Resources": [],
            },
        )
    )
    respx.get(f"{UPSTREAM}/v1/operations/op-456/await").mock(
        return_value=Response(
            200,
            json={
                "Id": "op-456",
                "Status": "Succeeded",
                "CreatedAt": "2026-05-10T10:00:00Z",
                "StartedAt": "2026-05-10T10:00:01Z",
                "CompletedAt": "2026-05-10T10:01:00Z",
                "Duration": 59,
                "Artifacts": [
                    {
                        "Id": "art-1",
                        "Filename": "log.txt",
                        "Type": "SolverLog",
                        "DownloadUrl": "/v1/artifacts/art-1",
                    }
                ],
                "Resources": [
                    {
                        "Id": "res-1",
                        "Path": "/me/forecasts/new-forecast",
                        "Version": 0,
                        "Role": "Output",
                    }
                ],
            },
        )
    )

    payload = {
        "input_forecast": "/me/forecasts/source",
        "output_forecast": "/me/forecasts/new-forecast",
        "solution_range": {"from_period": "2023Q2", "to_period": "2027Q4"},
        "wait_for_completion": True,
    }
    response = await client.post("/api/v1/solve", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "Succeeded"
    assert body["resources"][0]["path"] == "/me/forecasts/new-forecast"
    assert body["resources"][0]["role"] == "Output"


@respx.mock
async def test_solve_propagates_upstream_unauthorized(client: AsyncClient) -> None:
    respx.post(f"{UPSTREAM}/v1/operations/solve").mock(
        return_value=Response(401, json={"error": "invalid_token"}),
    )

    payload = {
        "input_forecast": "/me/forecasts/source",
        "output_forecast": "/me/forecasts/new-forecast",
        "solution_range": {"from_period": "2023Q2", "to_period": "2027Q4"},
    }
    response = await client.post("/api/v1/solve", json=payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Oxford Economics authentication failed"


async def test_solve_validation_error(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/solve",
        json={"input_forecast": "", "output_forecast": "x"},
    )
    assert response.status_code == 422
