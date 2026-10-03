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

import json
import re
import sys
from http import HTTPStatus
from pathlib import Path
from typing import Any, NamedTuple

import gateway_files

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
RESPONSE_KINDS = ("body", "text", "fixture", "hang", "drop")
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
# client.md gives these defaults.
DEFAULT_LEVEL = 1
DEFAULT_MAX_RETRIES = 2
# A scenario id in client.md: the method, a hyphen and the rule, in backticks.
SCENARIO_NAME = re.compile(r"`((?:lookup|reverse|autocomplete)-[a-z0-9-]+)`")
ERROR_ROW = re.compile(r"^\| [^|]+ \| `[a-z_]+` \|")
# The error map of client.md for a response that arrived. A test compares it with the table.
STATUS_CODES = {401: "unauthorized", 402: "insufficient_credits", 429: "rate_limited"}
RETRIED_STATUSES = (502, 503, 504)
CLIENT_ERRORS = range(400, 500)
RETRY_AFTER_STATUSES = (429, *RETRIED_STATUSES)
NO_RESPONSE_CODES = {"hang": "timeout", "drop": "network_error"}
METHOD_SCHEMAS = {
    "lookup": "LookupEnvelope",
    "reverse": "ReverseEnvelope",
    "autocomplete": "AutocompleteEnvelope",
}
# The fields of a lookup body that raise the level of the data, from the highest level down.
LEVEL_FIELDS = (
    ("point_geometry", 5),
    ("other_building_info", 4),
    ("building_use_status", 3),
    ("administrative_address", 2),
    ("recent_house_address", 2),
)
CONFIDENCES = ("high", "medium", "low")
UNIT_FIELDS = ("postcode", "distanceM", "confidence")


class ErrorRow(NamedTuple):
    """One row of the error table in client.md."""

    condition: str
    code: str
    scenarios: tuple[str, ...]


class Reply(NamedTuple):
    """What the mock server sends for one response of a scenario."""

    kind: str
    status: int | None
    body: Any
    headers: dict[str, str]


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


def error_code(status: int, api_code: str | None) -> str:
    """Return the error code that the error map of client.md gives for a response."""
    if status in STATUS_CODES:
        return STATUS_CODES[status]
    if status == HTTPStatus.FORBIDDEN:
        return "origin_not_allowed" if api_code == "origin_not_allowed" else "forbidden"
    if status == HTTPStatus.OK:
        return "unexpected_response"
    if status in RETRIED_STATUSES or status not in CLIENT_ERRORS:
        return "server_error"
    return "invalid_input"


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
        problems = truth_problems(scenario, fixtures)
    return [f"{name}: {problem}" for problem in problems]


def reply_of(response: dict[str, Any], fixtures: dict[str, Any]) -> Reply:
    """Return what the mock server sends for one response of a scenario."""
    kind = next(kind for kind in RESPONSE_KINDS if kind in response)
    headers = response.get("headers", {})
    if kind == "fixture":
        fixture = fixtures[response["fixture"]]
        return Reply(kind, fixture["status"], fixture["body"], headers)
    return Reply(kind, response.get("status"), response.get("body"), headers)


def last_reply(scenario: dict[str, Any], fixtures: dict[str, Any]) -> Reply | None:
    """Return the reply to the last attempt of a scenario, or None when no request goes out.

    The mock server repeats the last response when the requests outnumber the responses.
    """
    attempts = scenario["expect"]["attempts"]
    if attempts == 0:
        return None
    responses = scenario["responses"]
    return reply_of(responses[min(attempts, len(responses)) - 1], fixtures)


def api_code(body: Any) -> str | None:
    """Return the `error.code` of a body when it is text, as client.md reads it."""
    error = body.get("error") if isinstance(body, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    return code if isinstance(code, str) else None


def retry_after_ms(reply: Reply) -> int | None:
    """Return the wait of a valid Retry-After in seconds, when the status can carry one."""
    value = reply.headers.get("Retry-After", "")
    if reply.status not in RETRY_AFTER_STATUSES or not re.fullmatch(r"[0-9]+", value):
        return None
    return int(value) * 1000


def expected_error(reply: Reply | None) -> dict[str, Any]:
    """Return the error that client.md gives for the reply to the last attempt."""
    if reply is None or reply.status is None:
        code = "invalid_input" if reply is None else NO_RESPONSE_CODES[reply.kind]
        return {"code": code, "status": None, "apiCode": None, "retryAfterMs": None}
    return {
        "code": error_code(reply.status, api_code(reply.body)),
        "status": reply.status,
        "apiCode": api_code(reply.body),
        "retryAfterMs": retry_after_ms(reply),
    }


def level_received(data: dict[str, Any]) -> int:
    """Return the lookup level of the data, from the fields that it holds."""
    return next((level for field, level in LEVEL_FIELDS if field in data), DEFAULT_LEVEL)


def body_fields(call: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Return the fields of the result that client.md takes from the body, for one call."""
    if call["method"] == "lookup":
        return {
            "valid": data.get("valid"),
            "status": data.get("status"),
            "levelRequested": call.get("level", DEFAULT_LEVEL),
            "levelReceived": level_received(data),
        }
    if call["method"] == "autocomplete":
        codes = [suggestion.get("code") for suggestion in data.get("suggestions", [])]
        return {"segment": data.get("segment"), "suggestions": codes}
    fields = {key: data.get(key) for key in ("found", "area", "district", "state")}
    fields["radiusM"] = data.get("radius_m")
    unit = data.get("unit")
    fields["unit"] = None
    if isinstance(unit, dict):
        confidence = unit.get("confidence")
        fields["unit"] = {
            "postcode": unit.get("postcode"),
            "distanceM": unit.get("distance_m"),
            "confidence": confidence if confidence in CONFIDENCES else "low",
        }
    return fields


def result_fields(result: dict[str, Any], names: list[str]) -> dict[str, Any]:
    """Return the named fields of an expected result, in the form that body_fields gives."""
    fields = {name: result.get(name) for name in names}
    unit, suggestions = fields.get("unit"), fields.get("suggestions")
    if isinstance(unit, dict):
        fields["unit"] = {name: unit.get(name) for name in UNIT_FIELDS}
    if isinstance(suggestions, list):
        fields["suggestions"] = [suggestion.get("code") for suggestion in suggestions]
    return fields


def outcome_truth(call: dict[str, Any], outcome: dict[str, Any], reply: Reply | None) -> list[str]:
    """Return the problems of the outcome of a call against the reply to its last attempt."""
    if "error" in outcome:
        expected = expected_error(reply)
        if outcome["error"] == expected:
            return []
        return [
            f"The last response gives {json.dumps(expected)}, not {json.dumps(outcome['error'])}."
        ]
    data = reply.body.get("data") if reply and isinstance(reply.body, dict) else None
    if reply is None or reply.status != HTTPStatus.OK or not isinstance(data, dict):
        return ["A result needs a last response with the status 200 and an object in data."]
    expected = body_fields(call, data)
    stated = result_fields(outcome["result"], list(expected))
    return [
        f"The last response gives {name} {expected[name]!r}, not {stated[name]!r}."
        for name in expected
        if expected[name] != stated[name]
    ]


def fixture_method_problems(scenario: dict[str, Any], fixtures: dict[str, Any]) -> list[str]:
    """Return a problem for each fixture that answers another method than the calls use."""
    methods = {call["method"] for call in scenario["calls"]}
    allowed = {gateway_files.ERROR_SCHEMA, *(METHOD_SCHEMAS[method] for method in methods)}
    names = [response["fixture"] for response in scenario["responses"] if "fixture" in response]
    return [
        f"A {' or '.join(sorted(methods))} call cannot get {name}."
        for name in names
        if fixtures[name]["schema"] not in allowed
    ]


def truth_problems(scenario: dict[str, Any], fixtures: dict[str, Any]) -> list[str]:
    """Return the problems of a scenario whose outcomes disagree with its responses.

    With one call, the reply to the last attempt decides the outcome, as client.md says. Calls
    that share the responses, a cache or a queue get no such check, but each of their errors
    must still fit its own status and API code.
    """
    calls, expect = scenario["calls"], scenario["expect"]
    limit = len(calls) * (1 + scenario["client"].get("maxRetries", DEFAULT_MAX_RETRIES))
    problems = fixture_method_problems(scenario, fixtures)
    if expect["attempts"] > limit:
        problems.append(f"{expect['attempts']} attempts are more than the calls allow ({limit}).")
    if len(calls) == 1:
        return problems + outcome_truth(
            calls[0], expect["outcomes"][0], last_reply(scenario, fixtures)
        )
    errors = [outcome["error"] for outcome in expect["outcomes"] if "error" in outcome]
    return problems + [
        f"The status {error['status']} gives {error_code(error['status'], error['apiCode'])}, "
        f"not {error['code']}."
        for error in errors
        if error["status"] is not None
        and error_code(error["status"], error["apiCode"]) != error["code"]
    ]


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


def final_codes(scenario: dict[str, Any]) -> set[str]:
    """Return the error codes that the calls of a scenario end with."""
    return {
        outcome["error"]["code"] for outcome in scenario["expect"]["outcomes"] if "error" in outcome
    }


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
