#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Check the contract scenarios, and run every check of the OpenAPI file and the fixtures.

contract/README.md defines the format of a scenario. client.md defines the error codes, and it
names the scenario of each rule. A scenario must also agree with the responses that it lists: the
reply to the last attempt of a call decides its outcome. Run python3 scripts/contract_files.py.
It prints one line for each problem, and it exits with 1 when it finds one.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, NamedTuple

import gateway_files
import scenario_truth

ROOT = gateway_files.ROOT
CONTRACT = ROOT / "contract"
CLIENT_DOC = ROOT / "client.md"
TOP_FIELDS = ("version", "id", "description", "client", "calls", "responses", "expect")
CLIENT_OPTIONS = ("apiKey", "timeoutMs", "maxRetries", "cacheTtlMs")
ORDERS = ("parallel", "sequential")
# For each method: the fields that a call needs, and the fields that it can add.
CALL_FIELDS = {
    "lookup": ({"code"}, {"level"}),
    "reverse": ({"lat", "lng"}, {"maxDistanceM"}),
    "autocomplete": ({"q"}, set()),
}
RESPONSE_KINDS = scenario_truth.RESPONSE_KINDS
RESPONSE_EXTRAS = ("status", "headers", "delayMs")
EXPECT_FIELDS = {"attempts", "outcomes", "waitsMs", "maxInFlight", "request"}
ERROR_FIELDS = ("code", "status", "apiCode", "retryAfterMs")
REQUEST_FIELDS = ("method", "path", "query", "apiKey")
SHAPES = {
    "client": (dict, "an object"),
    "calls": (list, "a list"),
    "responses": (list, "a list"),
    "expect": (dict, "an object"),
}
# A scenario id in client.md: the method, a hyphen and the rule, in backticks.
SCENARIO_NAME = re.compile(r"`((?:lookup|reverse|autocomplete)-[a-z0-9-]+)`")
ERROR_ROW = re.compile(r"^\| [^|]+ \| `[a-z_]+` \|")


class ErrorRow(NamedTuple):
    """One row of the error table in client.md."""

    condition: str
    code: str
    scenarios: tuple[str, ...]


def error_rows(text: str) -> list[ErrorRow]:
    """Return the rows of the error table in the Errors section of client.md, in order."""
    section = text.partition("\n## Errors\n")[2].partition("\n## ")[0]
    if not section.strip():
        raise ValueError("client.md has no Errors section.")
    rows = []
    for line in section.splitlines():
        if ERROR_ROW.match(line):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            names = SCENARIO_NAME.findall(" ".join(cells[3:]))
            rows.append(ErrorRow(cells[0], cells[1].strip("`"), tuple(names)))
    return rows


def error_codes(path: Path = CLIENT_DOC) -> list[str]:
    """Return the error codes in the table of the Errors section of client.md, in order."""
    rows = error_rows(path.read_text(encoding="utf-8"))
    return list(dict.fromkeys(row.code for row in rows))


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
        extra = f" and can hold {', '.join(sorted(optional))}" if optional else ""
        return [f"A {method} call needs {', '.join(sorted(needed))}{extra}, and nothing else."]
    return []


def response_problems(response: Any, fixtures: dict[str, Any]) -> list[str]:
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
    if kind == "fixture" and (
        type(response["fixture"]) is not str or response["fixture"] not in fixtures
    ):
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
    if not {"attempts", "outcomes"} <= set(expect) or not isinstance(expect["outcomes"], list):
        return ["expect needs attempts and a list of outcomes."]
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


def scenario_problems(
    name: str, scenario: Any, fixtures: dict[str, Any], codes: list[str]
) -> list[str]:
    """Return the problems of one scenario, each line led by its file name.

    The checks of truth run only on a scenario that keeps the format.
    """
    if not isinstance(scenario, dict) or not set(TOP_FIELDS) <= set(scenario):
        return [f"{name}: a scenario needs the fields {', '.join(TOP_FIELDS)}."]
    wrong = [
        f"{name}: {field} must be {word}."
        for field, (kind, word) in SHAPES.items()
        if not isinstance(scenario[field], kind)
    ]
    if wrong:
        return wrong
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
    if not problems:
        problems = scenario_truth.truth_problems(scenario, fixtures)
    return [f"{name}: {problem}" for problem in problems]


def coverage_problems(scenarios: dict[str, Any], client_text: str) -> list[str]:
    """Return the problems of the link between client.md and the scenarios.

    client.md names the scenario of each rule. Each name needs a file, and each file needs a
    name. Each row of the error table names at least one scenario, and each of them ends with the
    code of its row.
    """
    named = set(SCENARIO_NAME.findall(client_text))
    problems = [
        f"client.md names the scenario {name}, which has no file."
        for name in sorted(named - set(scenarios))
    ]
    problems += [
        f"client.md names no rule for the scenario {name}."
        for name in sorted(set(scenarios) - named)
    ]
    for row in error_rows(client_text):
        if not row.scenarios:
            problems.append(f"The error row {row.condition} in client.md names no scenario.")
        problems += [
            f"The scenario {name} does not end with {row.code}, as its row says."
            for name in row.scenarios
            if name in scenarios and row.code not in final_codes(scenarios[name])
        ]
    return problems


def final_codes(scenario: Any) -> set[str]:
    """Return the error codes that the calls of a scenario end with.

    A scenario out of the format gives no code, and the check of its file names the fault.
    """
    expect = scenario.get("expect") if isinstance(scenario, dict) else None
    outcomes = expect.get("outcomes") if isinstance(expect, dict) else None
    errors = [item.get("error") for item in outcomes or [] if isinstance(item, dict)]
    return {error["code"] for error in errors if isinstance(error, dict) and "code" in error}


def synthetic_files() -> list[Path]:
    """Return the files that may hold only synthetic postcodes and mock keys.

    These are the fixtures, the scenarios, the docs beside them, client.md and the OpenAPI file.
    """
    folders = [*gateway_files.FIXTURES.rglob("*"), *CONTRACT.rglob("*")]
    files = [path for path in folders if path.suffix in (".json", ".md")]
    return sorted([*files, CLIENT_DOC, gateway_files.OPENAPI])


def all_problems() -> list[str]:
    """Return the problems of the OpenAPI file, the fixtures, the keys and the scenarios."""
    openapi = gateway_files.load_openapi()
    check = gateway_files.schema_check(openapi)
    fixtures = gateway_files.load_fixtures()
    scenarios = load_scenarios()
    codes = error_codes()
    problems = gateway_files.openapi_problems(openapi)
    for name, fixture in fixtures.items():
        shape = gateway_files.fixture_problems(name, fixture, check)
        problems += shape or gateway_files.fixture_response_problems(name, fixture, openapi)
    problems += gateway_files.key_problems(
        gateway_files.read_json(gateway_files.FIXTURES / "keys.json")
    )
    for name, scenario in scenarios.items():
        problems += scenario_problems(name, scenario, fixtures, codes)
    problems += coverage_problems(scenarios, CLIENT_DOC.read_text(encoding="utf-8"))
    files = synthetic_files()
    return (
        problems + gateway_files.postcode_problems(files) + gateway_files.key_text_problems(files)
    )


def main() -> int:
    """Print each problem, and return 1 when there is one."""
    problems = all_problems()
    for problem in problems:
        sys.stderr.write(problem + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
