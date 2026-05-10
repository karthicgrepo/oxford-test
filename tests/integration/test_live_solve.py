"""Live tests for the /solve endpoint.

Run with::

    # Quick tests only (queue a solve, return immediately):
    pytest -m "live and not slow" tests/integration/test_live_solve.py

    # Including the wait-for-completion test (can take several minutes):
    pytest -m live tests/integration/test_live_solve.py

By default the input forecast is the latest GEM release; override with
``OE_TEST_INPUT_FORECAST=/oxford-economics/releases/GEM/...``.
The output forecast goes under ``/me/api-test-solve-<timestamp>``;
override the prefix with ``OE_TEST_OUTPUT_PREFIX``.

Heads-up: the upstream rate limit is 10 enqueued operations per minute, and
each successful solve creates a new forecast in your account.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.live, pytest.mark.solve]

_QUEUED_OR_RUNNING = {"Queued", "InProgress"}
_TERMINAL = {"Succeeded", "Failed", "Cancelled"}


async def test_solve_returns_queued_operation(
    client: AsyncClient,
    latest_gem_forecast_path: str,
    output_forecast_path: str,
) -> None:
    """POST /api/v1/solve — fires a solve and returns immediately.

    Asserts the upstream accepted the request and returned a queued (or
    already-running / already-completed) ForecastOperation.
    """
    payload = {
        "input_forecast": latest_gem_forecast_path,
        "output_forecast": output_forecast_path,
        "solution_range": {"from_period": "2024Q1", "to_period": "2027Q4"},
        "operation_name": "pytest-live-solve",
    }

    response = await client.post("/api/v1/solve", json=payload)
    assert response.status_code == 202, response.text

    body = response.json()
    assert body["id"], body
    assert body["status"] in _QUEUED_OR_RUNNING | _TERMINAL

    print(
        f"\nSolve enqueued: id={body['id']} status={body['status']}\n"
        f"  input  = {latest_gem_forecast_path}\n"
        f"  output = {output_forecast_path}\n"
        f"  Check status: GET /api/v1/solve/operations/{body['id']}"
    )


async def test_get_operation_after_trigger(
    client: AsyncClient,
    latest_gem_forecast_path: str,
    output_forecast_path: str,
) -> None:
    """GET /api/v1/solve/operations/{id} — fetches non-blocking status."""
    trigger = await client.post(
        "/api/v1/solve",
        json={
            "input_forecast": latest_gem_forecast_path,
            "output_forecast": output_forecast_path,
            "solution_range": {"from_period": "2024Q1", "to_period": "2027Q4"},
            "operation_name": "pytest-live-solve-status",
        },
    )
    assert trigger.status_code == 202, trigger.text
    op_id = trigger.json()["id"]

    response = await client.get(f"/api/v1/solve/operations/{op_id}")
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["id"] == op_id
    assert body["status"] in _QUEUED_OR_RUNNING | _TERMINAL


@pytest.mark.slow
async def test_solve_wait_for_completion(
    client: AsyncClient,
    latest_gem_forecast_path: str,
    output_forecast_path: str,
) -> None:
    """POST /api/v1/solve with wait_for_completion=true.

    Polls the upstream /await endpoint and returns only once the operation
    reaches a terminal state. Slow — opt in with ``pytest -m live`` (drop
    ``not slow``) or by selecting this test by name.
    """
    payload = {
        "input_forecast": latest_gem_forecast_path,
        "output_forecast": output_forecast_path,
        "solution_range": {"from_period": "2024Q1", "to_period": "2027Q4"},
        "operation_name": "pytest-live-solve-wait",
        "wait_for_completion": True,
    }

    response = await client.post("/api/v1/solve", json=payload)
    assert response.status_code == 202, response.text

    body = response.json()
    assert body["status"] in _TERMINAL, body

    print(
        f"\nSolve completed: id={body['id']} status={body['status']} "
        f"duration={body.get('duration')}s"
    )

    if body["status"] != "Succeeded":
        pytest.fail(
            f"Solve did not succeed: status={body['status']} "
            f"failure_reason={body.get('failure_reason')}"
        )

    output_resources = [
        r for r in body.get("resources", []) if r.get("role") == "Output"
    ]
    assert output_resources, "Expected at least one Output resource on a successful solve"
