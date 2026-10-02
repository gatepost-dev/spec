#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Check the contract scenarios, and run every check of the OpenAPI file and the fixtures.

contract/README.md defines the format of a scenario, and client.md defines the error codes.
Run python3 scripts/contract_files.py. It prints one line for each problem, and it exits with 1
when it finds one.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import gateway_files

ROOT = gateway_files.ROOT
CONTRACT = ROOT / "contract"
CLIENT_DOC = ROOT / "client.md"
TOP_FIELDS = ("version", "id", "description", "client", "calls", "responses", "expect")
CLIENT_OPTIONS = ("apiKey", "timeoutMs", "maxRetries", "cacheTtlMs")
ORDERS = ("parallel", "sequential")
# For each method: the fields that a call needs, and the fields that it can add.
CALL_FIELDS = {
    "lookup": ({"code", "level"}, set()),
    "reverse": ({"lat", "lng"}, {"maxDistanceM"}),
    "autocomplete": ({"q"}, set()),
}
RESPONSE_KINDS = ("body", "text", "fixture", "hang", "drop")
RESPONSE_EXTRAS = ("status", "headers", "delayMs")
EXPECT_FIELDS = {"attempts", "outcomes", "waitsMs", "maxInFlight", "request"}
ERROR_FIELDS = ("code", "status", "apiCode", "retryAfterMs")
REQUEST_FIELDS = ("method", "path", "query", "apiKey")
# The minimum that the design asks for, beside one scenario for each error code: each retry
# rule, Retry-After, the timeout, request sharing, the queue limit, unknown fields and values,
# each rule of input and the plain form of a number.
REQUIRED_SCENARIOS = (
    "lookup-retry-502",
    "lookup-retry-503",
    "lookup-retry-504",
    "lookup-retries-exhausted",
    "lookup-network-error",
    "lookup-retry-after",
    "lookup-rate-limited",
    "lookup-timeout",
    "autocomplete-timeout",
    "lookup-shared-request",
    "lookup-queue-limit",
    "lookup-unknown-fields",
    "reverse-unknown-fields",
    "autocomplete-unknown-fields",
    "lookup-unknown-status",
    "lookup-invalid-level",
    "reverse-invalid-lat",
    "reverse-invalid-lng",
    "reverse-invalid-max-distance",
    "reverse-plain-decimal",
    "reverse-whole-number",
    "lookup-deadline",
    "lookup-retry-after-503",
    "lookup-retry-after-invalid",
    "lookup-shared-spellings",
    "lookup-missing-valid",
    "lookup-status-not-text",
    "reverse-missing-found",
    "autocomplete-suggestions-not-list",
)


def error_codes(path: Path = CLIENT_DOC) -> list[str]:
    """Return the error codes in the table of the Errors section of client.md, in order."""
    section = path.read_text(encoding="utf-8").partition("\n## Errors\n")[2].partition("\n## ")[0]
    if not section.strip():
        raise ValueError(f"{path} has no Errors section.")
    codes = re.findall(r"^\| [^|]+ \| `([a-z_]+)` \|", section, flags=re.MULTILINE)
    return list(dict.fromkeys(codes))


def load_scenarios(root: Path = CONTRACT) -> dict[str, Any]:
    """Return each scenario by its file name without `.json`."""
    return {path.stem: gateway_files.read_json(path) for path in sorted(root.glob("*.json"))}


def call_problems(call: Any) -> list[str]:
    """Return the problems of one call."""
    method = call.get("method") if isinstance(call, dict) else None
    if method not in CALL_FIELDS:
        return [f"A call needs a method: one of {', '.join(CALL_FIELDS)}."]
    needed, optional = CALL_FIELDS[method]
    fields = set(call) - {"method"}
    if not needed <= fields <= needed | optional:
        return [f"A {method} call needs {', '.join(sorted(needed))}, and nothing else."]
    return []


def response_problems(response: Any, fixtures: set[str]) -> list[str]:
    """Return the problems of one response of the mock server."""
    if not isinstance(response, dict):
        return ["Each response must be an object."]
    kinds = [kind for kind in RESPONSE_KINDS if kind in response]
    if len(kinds) != 1 or set(response) - {*RESPONSE_KINDS, *RESPONSE_EXTRAS}:
        return [f"A response needs exactly one of {', '.join(RESPONSE_KINDS)}."]
    kind = kinds[0]
    problems = []
    if kind in ("body", "text") and type(response.get("status")) is not int:
        problems.append(f"A {kind} response needs an integer status.")
    if kind not in ("body", "text") and "status" in response:
        problems.append(f"A {kind} response must not have a status.")
    if kind in ("hang", "drop") and (response[kind] is not True or "headers" in response):
        problems.append(f"A {kind} response needs the value true, and no headers.")
    if kind == "fixture" and response["fixture"] not in fixtures:
        problems.append(f"No fixture is named {response['fixture']}.")
    delay = response.get("delayMs", 0)
    if type(delay) is not int or delay < 0:
        problems.append("delayMs must be a whole number of 0 or more.")
    return problems


def outcome_problems(outcome: Any, codes: list[str]) -> list[str]:
    """Return the problems of one outcome."""
    if not isinstance(outcome, dict) or len(outcome) != 1 or set(outcome) - {"result", "error"}:
        return ["An outcome needs exactly one of result and error."]
    error = outcome.get("error")
    if error is None:
        return []
    if not isinstance(error, dict) or tuple(error) != ERROR_FIELDS:
        return [f"An error needs the fields {', '.join(ERROR_FIELDS)}."]
    if error["code"] not in codes:
        return [f"The error code {error['code']} is not in client.md."]
    return []


def expect_problems(scenario: dict[str, Any], codes: list[str]) -> list[str]:
    """Return the problems of the expect object of a scenario."""
    expect = scenario["expect"]
    if not isinstance(expect, dict) or not {"attempts", "outcomes"} <= set(expect):
        return ["expect needs attempts and outcomes."]
    problems = []
    if set(expect) - EXPECT_FIELDS:
        problems.append(f"expect has an unknown field: {sorted(set(expect) - EXPECT_FIELDS)}.")
    if len(expect["outcomes"]) != len(scenario["calls"]):
        problems.append("expect needs one outcome for each call.")
    if (expect["attempts"] == 0) != (scenario["responses"] == []):
        problems.append("No attempt means no response, and the other way round.")
    waits = expect.get("waitsMs")
    if waits is not None and (len(scenario["calls"]) != 1 or len(waits) != expect["attempts"] - 1):
        problems.append("waitsMs needs one call, and one wait less than the attempts.")
    if waits is not None and any(wait["min"] > wait["max"] for wait in waits):
        problems.append("Each wait needs a min that is not above its max.")
    if "request" in expect and tuple(expect["request"]) != REQUEST_FIELDS:
        problems.append(f"request needs the fields {', '.join(REQUEST_FIELDS)}.")
    for outcome in expect["outcomes"]:
        problems += outcome_problems(outcome, codes)
    return problems


def scenario_problems(name: str, scenario: Any, fixtures: set[str], codes: list[str]) -> list[str]:
    """Return the problems of one scenario, each line led by its file name."""
    if not isinstance(scenario, dict) or not set(TOP_FIELDS) <= set(scenario):
        return [f"{name}: a scenario needs the fields {', '.join(TOP_FIELDS)}."]
    problems = []
    if scenario["version"] != 1 or scenario["id"] != name:
        problems.append("The version must be 1, and the id must equal the file name.")
    if set(scenario) - {*TOP_FIELDS, "order"}:
        problems.append("The scenario has a field that the format does not name.")
    if set(scenario["client"]) - set(CLIENT_OPTIONS):
        problems.append(f"client can hold only {', '.join(CLIENT_OPTIONS)}.")
    if (scenario.get("order") in ORDERS) != (len(scenario["calls"]) > 1):
        problems.append(f"Two or more calls need an order: {', '.join(ORDERS)}.")
    for call in scenario["calls"]:
        problems += call_problems(call)
    for response in scenario["responses"]:
        problems += response_problems(response, fixtures)
    problems += expect_problems(scenario, codes)
    return [f"{name}: {problem}" for problem in problems]


def coverage_problems(scenarios: dict[str, Any], codes: list[str]) -> list[str]:
    """Return the error codes and the required scenarios that no scenario covers."""
    reached = {
        outcome["error"]["code"]
        for scenario in scenarios.values()
        for outcome in scenario["expect"]["outcomes"]
        if "error" in outcome
    }
    problems = [
        f"No scenario ends with the error code {code}." for code in codes if code not in reached
    ]
    problems += [
        f"The scenario {name} is missing." for name in REQUIRED_SCENARIOS if name not in scenarios
    ]
    return problems


def all_problems() -> list[str]:
    """Return the problems of the OpenAPI file, the fixtures, the keys and the scenarios."""
    openapi = gateway_files.load_openapi()
    check = gateway_files.schema_check(openapi)
    fixtures = gateway_files.load_fixtures()
    scenarios = load_scenarios()
    codes = error_codes()
    problems = gateway_files.openapi_problems(openapi)
    for name, fixture in fixtures.items():
        problems += gateway_files.fixture_problems(name, fixture, check)
    used = gateway_files.schemas_in_responses(openapi)
    problems += [
        f"Fixture {name} uses {fixture['schema']}, which no response uses."
        for name, fixture in fixtures.items()
        if fixture.get("schema") not in used
    ]
    problems += gateway_files.key_problems(
        gateway_files.read_json(gateway_files.FIXTURES / "keys.json")
    )
    for name, scenario in scenarios.items():
        problems += scenario_problems(name, scenario, set(fixtures), codes)
    problems += coverage_problems(scenarios, codes)
    files = sorted([*gateway_files.FIXTURES.rglob("*.json"), *CONTRACT.glob("*.json")])
    return problems + gateway_files.postcode_problems(files)


def main() -> int:
    """Print each problem, and return 1 when there is one."""
    problems = all_problems()
    for problem in problems:
        sys.stderr.write(problem + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
