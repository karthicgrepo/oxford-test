# Oxford Economics API Service

A FastAPI service that wraps the [Oxford Economics GMWO API](https://model.oxfordeconomics.com/api/docs/) and exposes the `solve` operation through a clean, documented HTTP interface.

## Features

- Async, layered architecture (router -> service -> client) ready to extend with new GMWO endpoints.
- Pydantic v2 schemas mirroring the upstream contracts.
- Centralised configuration via environment variables (`pydantic-settings`).
- Structured logging, correlation-friendly error handling, retry with exponential backoff.
- Auto-generated OpenAPI docs at `/docs` and `/redoc`.

## Reference

A snapshot of the upstream OpenAPI spec is checked in at
[`docs/oxford-gmwo-swagger.json`](docs/oxford-gmwo-swagger.json). Refresh it
from <https://model.oxfordeconomics.com/api/v1/swagger/swagger.json> when
upstream changes.

## Project layout

```
app/
  main.py                # FastAPI factory, lifespan, middleware
  core/
    config.py            # Settings (env-driven)
    logging.py           # Logging configuration
    exceptions.py        # Custom exceptions + handlers
  clients/
    oxford_client.py     # Async httpx client for Oxford Economics API
  schemas/
    solve.py             # Pydantic models for the solve endpoint
    token.py             # Pydantic models for access tokens
  services/
    solve_service.py     # Business logic around solve operations
    token_service.py     # Token rotation helper
  api/
    deps.py              # FastAPI dependencies (DI)
    v1/
      router.py          # Aggregates v1 routers
      endpoints/
        health.py
        solve.py
        token.py
tests/
  conftest.py
  test_solve.py
```

## Authentication

The Oxford Economics GMWO API uses long-lived Bearer tokens. According to the
authentication section of the GMWO swagger spec, the first token is generated
through the **interactive Swagger UI** itself, after you sign in:

1. Sign in to GMWO and visit the API explorer:
   <https://model.oxfordeconomics.com/api/v1/swagger>
2. Open the **Access Token** section and select
   `POST /v1/access-token/generate`.
3. Click **Try it out**, set a `Name` in the request body, then click
   **Execute**.
4. Copy the `Value` field from the response body — this is your bearer token.

> The token `Value` is shown **only once**; it cannot be retrieved again. If
> lost, revoke (`DELETE /v1/access-token/{id}`) and generate a new one.

Put the token in `.env` as `OE_API_TOKEN`. The service then sends
`Authorization: Bearer <token>` on every upstream request.

> **Bearer tokens cannot mint other Bearer tokens.** Calling `POST
> /v1/access-token/generate` with `Authorization: Bearer <…>` is rejected
> upstream with `400 Cannot create access token unless authenticated as a
> user.` — token generation requires the browser SSO session that the Swagger
> UI uses. To rotate, repeat steps 1-4 above. This service therefore exposes
> only `GET /api/v1/tokens` (list); there is no programmatic generate.

> Heads-up: don't confuse GMWO (`model.oxfordeconomics.com`) with the Databank
> API at `data.oxfordeconomics.com`, which uses a different `api-key` header.
> This project targets the GMWO model API only.

## Quickstart

```powershell
# 1. Create and activate a venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install
pip install -e ".[dev]"

# 3. Configure
copy .env.example .env
# edit .env and set OE_API_TOKEN

# 4. Run
uvicorn app.main:app --reload
```

Then open <http://localhost:8000/docs>.

## Calling the solve endpoint

```bash
curl -X POST http://localhost:8000/api/v1/solve \
  -H "Content-Type: application/json" \
  -d '{
    "input_forecast": "/me/forecasts/source",
    "output_forecast": "/me/forecasts/new-forecast",
    "solution_range": { "from_period": "2023Q2", "to_period": "2027Q4" },
    "commands_file": "/me/commands/myfile",
    "wait_for_completion": true
  }'
```

When `wait_for_completion` is `true` the service polls `GET /v1/operations/{id}/await` until the operation leaves the `Queued`/`InProgress` states, mirroring the [reference notebook](https://github.com/OxfordEconomics/gmwo-api-examples/blob/main/solve/solve.ipynb).

## Testing

There are two test suites:

| Suite                    | Hits real upstream? | Marker        | Default? |
| ------------------------ | ------------------- | ------------- | -------- |
| `tests/test_solve.py`    | No (mocked)         | _none_        | yes      |
| `tests/integration/`     | **Yes**             | `live`        | no       |

Run unit tests (offline, fast):

```powershell
pytest
```

### Live tests — opt-in

Live tests use the real `OE_API_TOKEN` from `.env` and call the actual Oxford
Economics API. Solve tests create real forecasts in your account and consume
the upstream `10 enqueued operations / minute` quota.

```powershell
# All quick live tests (skip the long-running wait test)
pytest -m "live and not slow"

# Just the token tests (list)
pytest -m "live and tokens"

# Just the solve tests (queue only — fast)
pytest -m "live and solve and not slow"

# A specific test
pytest tests/integration/test_live_solve.py::test_solve_returns_queued_operation

# The wait-for-completion solve test (can take several minutes)
pytest tests/integration/test_live_solve.py::test_solve_wait_for_completion
```

Override the input/output forecast paths if you don't want defaults:

```powershell
$env:OE_TEST_INPUT_FORECAST = "/oxford-economics/releases/GEM/Apr26_2 25yr"
$env:OE_TEST_OUTPUT_PREFIX  = "/me/my-test-runs"
pytest -m "live and solve and not slow"
```

### Practical recipes

- **"I want to fire a quick solve":** `pytest tests/integration/test_live_solve.py::test_solve_returns_queued_operation -s`
- **"I want to fire a solve and wait for it to finish":** `pytest tests/integration/test_live_solve.py::test_solve_wait_for_completion -s`
- **"I want to see what tokens I already have":** `pytest tests/integration/test_live_tokens.py::test_list_tokens -s`
- **"I want to mint a new bearer token":** Cannot be done from code — see the
  [Authentication](#authentication) section. Use the Swagger UI in your browser.

## Extending

Add a new GMWO operation by:

1. Adding the request/response models under `app/schemas/`.
2. Adding a method on `OxfordEconomicsClient` in `app/clients/oxford_client.py`.
3. Adding a service in `app/services/` that orchestrates the call.
4. Adding a router in `app/api/v1/endpoints/` and registering it in `app/api/v1/router.py`.
