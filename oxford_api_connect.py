"""Simple single-file connector for the Oxford Economics GMWO API.

Usage:
    export OE_API_TOKEN="your-token-here"   # or set it in the script
    python oxford_api_connect.py

Requires: pip install requests
"""

import os
import time
import sys
import json
import requests

# ---------------------------------------------------------------------------
# Config — edit these or set the OE_API_TOKEN environment variable
# ---------------------------------------------------------------------------
BASE_URL   = "https://model.oxfordeconomics.com/api"
#API_TOKEN  = os.environ.get("OE_API_TOKEN", "YOUR_TOKEN_HERE")
API_TOKEN  = "DGHM5i9XoT9qXw1MVoUlWDc1ekyd5Vw7uCRhKX96x5V112o="
TIMEOUT    = 60          # seconds per request
POLL_SLEEP = 3           # seconds between /await polls


# ---------------------------------------------------------------------------
# Core HTTP helper
# ---------------------------------------------------------------------------
SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept":        "application/json",
    "Content-Type":  "application/json",
})


def _request(method: str, path: str, **kwargs) -> dict | list | None:
    url = f"{BASE_URL}{path}"
    resp = SESSION.request(method, url, timeout=TIMEOUT, **kwargs)
    if resp.status_code == 401:
        sys.exit("Authentication failed — check your API token.")
    if resp.status_code == 429:
        sys.exit("Rate limit exceeded (429). Slow down requests.")
    resp.raise_for_status()
    return resp.json() if resp.content else None


def get(path: str, **params) -> dict | list | None:
    return _request("GET", path, params=params or None)


def post(path: str, body: dict) -> dict | list | None:
    return _request("POST", path, json=body)


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------

def get_current_user() -> dict:
    """GET /v1/users/me — who am I?"""
    return get("/v1/users/me")


def browse_resources(identifier: str = "me", include_all_file_types: bool = False) -> dict:
    """GET /v1/resources/{identifier} — list files and directories.

    identifier examples:
        "me"              → your personal root folder
        "us"              → your organisation root folder
        "me/forecasts"    → a subfolder called 'forecasts' in your space
        "=<forecast-id>"  → look up by id (prefix with =)
    """
    return get(f"/v1/resources/{identifier}", includeAllFileTypes=include_all_file_types)


def get_forecast(forecast_id: str) -> dict:
    """GET /v1/forecasts/{id} — fetch forecast metadata and version list."""
    return get(f"/v1/forecasts/{forecast_id}")


def get_forecast_groups(forecast_id: str) -> list:
    """GET /v1/forecast-contents/{id}/groups — get groups (sectors) in a forecast."""
    return get(f"/v1/forecast-contents/{forecast_id}/groups")


def get_forecast_indicators(forecast_id: str) -> list:
    """GET /v1/forecast-contents/{id}/indicators — get available indicators."""
    return get(f"/v1/forecast-contents/{forecast_id}/indicators")


def get_variables(forecast_id: str, variable_keys: list[dict]) -> list:
    """POST /v1/forecast-contents/{id}/variables — fetch time-series data.

    variable_keys: list of {"GroupCode": "GBR", "IndicatorCode": "GDP"}
    """
    return post(f"/v1/forecast-contents/{forecast_id}/variables", variable_keys)


def get_single_variable(forecast_id: str, group_code: str, indicator_code: str) -> dict:
    """GET /v1/forecast-contents/{id}/variable/{sectorCode}/{indicatorCode}"""
    return get(f"/v1/forecast-contents/{forecast_id}/variable/{group_code}/{indicator_code}")


def trigger_solve(
    input_forecast: str,
    output_forecast: str,
    solution_range_from: str,
    solution_range_to: str,
    commands: str | None = None,
    commands_file: str | None = None,
    groups: list[str] | None = None,
    operation_name: str | None = None,
) -> dict:
    """POST /v1/operations/solve — enqueue a model solve.

    Returns a ForecastOperation object immediately (status = Queued).
    Use poll_until_done() to wait for completion.

    Args:
        input_forecast:       path to source forecast, e.g. "me/baseline"
        output_forecast:      path for the result, e.g. "me/baseline_solved"
        solution_range_from:  start period, e.g. "2023Q1"
        solution_range_to:    end period,   e.g. "2027Q4"
        commands:             inline 3FS command string (mutually exclusive with commands_file)
        commands_file:        path to a stored commands/import file
        groups:               list of group codes to solve (None = all)
        operation_name:       a friendly label shown in the UI
    """
    payload = {
        "InputForecast":  input_forecast,
        "OutputForecast": output_forecast,
        "SolutionRange":  {"From": solution_range_from, "To": solution_range_to},
    }
    if commands:
        payload["Commands"] = commands
    if commands_file:
        payload["CommandsFile"] = commands_file
    if groups:
        payload["Groups"] = groups
    if operation_name:
        payload["OperationName"] = operation_name

    return post("/v1/operations/solve", payload)


def trigger_apply(
    input_forecast: str,
    output_forecast: str,
    commands: str | None = None,
    commands_file: str | None = None,
    operation_name: str | None = None,
) -> dict:
    """POST /v1/operations/apply — apply commands without solving."""
    payload = {
        "InputForecast":  input_forecast,
        "OutputForecast": output_forecast,
    }
    if commands:
        payload["Commands"] = commands
    if commands_file:
        payload["CommandsFile"] = commands_file
    if operation_name:
        payload["OperationName"] = operation_name
    return post("/v1/operations/apply", payload)


def trigger_export(
    input_forecast: str,
    range_from: str,
    range_to: str,
    series_selection: list[dict] | None = None,
    fmt: str | None = None,
    annual_rollup: bool | None = None,
    operation_name: str | None = None,
) -> dict:
    """POST /v1/operations/export — export forecast data to a file.

    series_selection: list of {"Indicator": "GDP", "Location": "GBR"}
    fmt:              e.g. "xlsx"
    """
    payload: dict = {
        "InputForecast": input_forecast,
        "Range":         {"From": range_from, "To": range_to},
    }
    if series_selection:
        payload["SeriesSelection"] = series_selection
    if fmt:
        payload["Format"] = fmt
    if annual_rollup is not None:
        payload["AnnualRollup"] = annual_rollup
    if operation_name:
        payload["OperationName"] = operation_name
    return post("/v1/operations/export", payload)


def get_operation(operation_id: str) -> dict:
    """GET /v1/operations/{id} — non-blocking status check."""
    return get(f"/v1/operations/{operation_id}")


def poll_until_done(operation_id: str, verbose: bool = True) -> dict:
    """Poll /v1/operations/{id}/await until the operation reaches a terminal state.

    The /await endpoint blocks server-side for ~60 s per call, so we loop
    until status is Succeeded, Failed, or Cancelled.
    """
    terminal = {"Succeeded", "Failed", "Cancelled"}
    while True:
        op = get(f"/v1/operations/{operation_id}/await")
        status = op.get("Status", "")
        if verbose:
            print(f"  operation {operation_id}: {status}")
        if status in terminal:
            return op
        time.sleep(POLL_SLEEP)


def list_access_tokens() -> list:
    """GET /v1/access-token — list active tokens for the current user."""
    return get("/v1/access-token")


def generate_access_token(name: str) -> dict:
    """POST /v1/access-token/generate — create a new access token."""
    return post("/v1/access-token/generate", {"Name": name})


def revoke_access_token(token_id: str) -> None:
    """DELETE /v1/access-token/{id} — permanently deactivate a token."""
    _request("DELETE", f"/v1/access-token/{token_id}")


# ---------------------------------------------------------------------------
# Demo / quick-start
# ---------------------------------------------------------------------------

def _pp(label: str, obj) -> None:
    print(f"\n{'='*60}\n{label}\n{'='*60}")
    print(json.dumps(obj, indent=2, default=str))


def main():
    if API_TOKEN == "YOUR_TOKEN_HERE":
        sys.exit("Set OE_API_TOKEN env var or edit API_TOKEN in this file before running.")

    # 1. Who am I?
    me = get_current_user()
    _pp("Current user", me)

    # 2. Browse your root folder
    root = browse_resources("me")
    _pp("My resources", root)

    #3. Example: trigger a solve
     #  Edit these paths to match real forecasts in your account.

    op = trigger_solve(
       input_forecast="me/baseline",
       output_forecast="me/baseline_solved",
       solution_range_from="2023Q1",
       solution_range_to="2027Q4",
       operation_name="my-solve",
    )
    _pp("Solve queued", op)
    result = poll_until_done(op["Id"])
    _pp("Solve result", result)

    # 4. Example: fetch variable data from a forecast
    #    (replace with a real forecast id from step 2)
    #
    #    forecast_id = "your-forecast-id-here"
    #    data = get_variables(
    #        forecast_id,
    #        [{"GroupCode": "GBR", "IndicatorCode": "GDP"}],
    #    )
    #    _pp("GDP data", data)

    print("\nDone. Uncomment the example blocks above to run solve/export/data flows.")


if __name__ == "__main__":
    main()
