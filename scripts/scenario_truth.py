# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Check that a contract scenario agrees with client.md and with the responses that it lists.

The check plays the scenario as client.md says that a client does: it counts the attempts and the
waits of each call, shares a request or a kept result where client.md allows it, and takes the
outcome of each call from the reply to its last attempt. Each check returns a list of problems.
"""

from __future__ import annotations

import json
import math
import re
from decimal import Decimal
from http import HTTPStatus
from typing import Any, NamedTuple

from gateway_files import ERROR_SCHEMA

# client.md gives these defaults.
DEFAULT_LEVEL = 1
LEVELS = range(1, 6)
DEFAULT_MAX_RETRIES = 2
DEFAULT_TIMEOUT_MS = 8000
AUTOCOMPLETE_TIMEOUT_MS = 15000
MAX_IN_FLIGHT = 4
LONGEST_RETRY_AFTER_MS = 10_000
MAX_DISTANCE_M = 250
AUTOCOMPLETE_LENGTH = 11
# The error map of client.md for a response that arrived. A test compares it with the table.
STATUS_CODES = {401: "unauthorized", 402: "insufficient_credits", 429: "rate_limited"}
RETRIED_STATUSES = (502, 503, 504)
CLIENT_ERRORS = range(400, 500)
RETRY_AFTER_STATUSES = (429, *RETRIED_STATUSES)
NO_RESPONSE_CODES = {"hang": "timeout", "drop": "network_error"}
RESPONSE_KINDS = ("body", "text", "fixture", "hang", "drop")
METHOD_SCHEMAS = {
    "lookup": "LookupEnvelope",
    "reverse": "ReverseEnvelope",
    "autocomplete": "AutocompleteEnvelope",
}
METHOD_PATHS = {
    "lookup": "/v1/lookup",
    "reverse": "/v1/search/reverse",
    "autocomplete": "/v1/search/autocomplete",
}
# The fields of a lookup body that raise the level of the data, from the highest level down.
LEVEL_FIELDS = (
    ("point_geometry", 5),
    ("other_building_info", 4),
    ("building_use_status", 3),
    ("administrative_address", 2),
    ("recent_house_address", 2),
)
ADDRESS_FIELDS = {
    "stateName": "state_name",
    "lgaName": "lga_name",
    "localityName": "locality_name",
    "zone": "zone",
}
UNIT_NAMES = {
    "stateName": "state_name",
    "lgaName": "lga_name",
    "localityName": "locality_name",
    "address": "address",
}
CONFIDENCES = ("high", "medium", "low")
# A full postcode after the core's normalising: no spaces and no hyphens, in upper case.
COMPACT_POSTCODE = re.compile(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{3}[A-Z]{2}[0-9]{2}")
AUTOCOMPLETE_TEXT = re.compile(rf"[A-Z0-9]{{1,{AUTOCOMPLETE_LENGTH}}}")


class Reply(NamedTuple):
    """What the mock server sends for one response of a scenario."""

    kind: str
    status: int | None
    body: Any
    headers: dict[str, str]
    delay_ms: int


class Played(NamedTuple):
    """The outcome of one call as client.md plays it."""

    reply: Reply | None
    attempts: int
    waits: list[dict[str, int]]


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


def query_number(number: float) -> str:
    """Write a number as client.md asks: the shortest decimal form, with no exponent.

    A whole number has no fraction part, and a negative zero is 0.
    """
    text = format(Decimal(repr(float(number))), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def compact(text: str) -> str:
    """Return text as the core normalises it: no spaces and no hyphens, in upper case."""
    return re.sub(r"[\s-]", "", text).upper()


def canonical(code: str) -> str:
    """Return the canonical form of a compact full postcode."""
    return "-".join((code[:2], code[2:4], code[4:7], code[7:9], code[9:]))


def in_range(value: Any, low: float, high: float) -> bool:
    """Tell whether a value is a finite number from low to high."""
    number = type(value) in (int, float) and math.isfinite(value)
    return number and low <= value <= high


def call_key(call: dict[str, Any]) -> tuple[Any, ...] | None:
    """Return the key that shares a request and a kept result, or None for input that fails.

    client.md makes the key from the method and the canonical form of the arguments.
    """
    method = call["method"]
    if method == "lookup":
        code, level = compact(call["code"]), call.get("level", DEFAULT_LEVEL)
        valid = COMPACT_POSTCODE.fullmatch(code) and type(level) is int and level in LEVELS
        return (method, canonical(code), level) if valid else None
    if method == "autocomplete":
        text = compact(call["q"])
        return (method, text) if AUTOCOMPLETE_TEXT.fullmatch(text) else None
    distance = call.get("maxDistanceM", 0)
    if not (
        in_range(call["lat"], -90, 90)
        and in_range(call["lng"], -180, 180)
        and in_range(distance, 0, MAX_DISTANCE_M)
    ):
        return None
    return (method, call["lat"], call["lng"], call.get("maxDistanceM"))


def expected_request(call: dict[str, Any], client: dict[str, Any]) -> dict[str, Any]:
    """Return the request that client.md gives for a call with valid input."""
    key = call_key(call)
    if call["method"] == "lookup" and key:
        query = {"code": key[1], "level": str(key[2])}
    elif call["method"] == "autocomplete" and key:
        query = {"q": key[1]}
    else:
        query = {"lat": query_number(call["lat"]), "lng": query_number(call["lng"])}
        if "maxDistanceM" in call:
            query["max_distance_m"] = query_number(call["maxDistanceM"])
    return {
        "method": "GET",
        "path": METHOD_PATHS[call["method"]],
        "query": query,
        "apiKey": client.get("apiKey"),
    }


def reply_of(response: dict[str, Any], fixtures: dict[str, Any]) -> Reply:
    """Return what the mock server sends for one response of a scenario."""
    kind = next(kind for kind in RESPONSE_KINDS if kind in response)
    headers, delay = response.get("headers", {}), response.get("delayMs", 0)
    if kind == "fixture":
        fixture = fixtures[response["fixture"]]
        return Reply(kind, fixture["status"], fixture["body"], headers, delay)
    return Reply(kind, response.get("status"), response.get("body"), headers, delay)


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


def backoff(retry: int) -> dict[str, int]:
    """Return the bounds of the client's own wait before a retry, the first being 1."""
    shortest = 500 * 2 ** (retry - 1)
    return {"min": shortest, "max": shortest + 250}


def deadline_ms(timeout_ms: int, max_retries: int) -> int:
    """Return the total deadline of a call: every timeout, and the longest wait of each retry."""
    waits = sum(backoff(retry)["max"] for retry in range(1, max_retries + 1))
    return (1 + max_retries) * timeout_ms + waits


def next_wait(reply: Reply, method: str, retry: int) -> dict[str, int] | None:
    """Return the wait before the next attempt, or None when client.md does not retry."""
    if reply.kind == "hang":
        return None if method == "autocomplete" else backoff(retry)
    if reply.kind == "drop":
        return backoff(retry)
    asked = retry_after_ms(reply)
    short = asked if asked is not None and asked <= LONGEST_RETRY_AFTER_MS else None
    if reply.status == HTTPStatus.TOO_MANY_REQUESTS:
        return None if short is None else {"min": short, "max": short}
    if reply.status in RETRIED_STATUSES:
        return backoff(retry) if short is None else {"min": short, "max": short}
    return None


def play_call(
    call: dict[str, Any], client: dict[str, Any], replies: list[Reply], *, sent: int
) -> Played:
    """Return the attempts, the waits and the last reply of one call that sends a request.

    sent is the number of requests before this call. The mock server repeats its last reply.
    Elapsed time counts each wait at its upper bound, as the deadline of client.md does.
    """
    retries = client.get("maxRetries", DEFAULT_MAX_RETRIES)
    default = AUTOCOMPLETE_TIMEOUT_MS if call["method"] == "autocomplete" else DEFAULT_TIMEOUT_MS
    timeout = client.get("timeoutMs", default)
    deadline = deadline_ms(timeout, retries)
    attempt, elapsed = 1, 0
    waits: list[dict[str, int]] = []
    while True:
        reply = replies[min(sent + attempt, len(replies)) - 1]
        elapsed += timeout if reply.kind == "hang" else min(reply.delay_ms, timeout)
        wait = next_wait(reply, call["method"], attempt)
        if wait is None or attempt > retries or elapsed + wait["max"] > deadline:
            return Played(reply, attempt, waits)
        waits.append(wait)
        elapsed += wait["max"]
        attempt += 1


def broken_body(method: str, body: Any) -> bool:
    """Tell whether a 200 body breaks client.md, so that the call gives unexpected_response."""
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return True
    if method == "lookup":
        status = data.get("status")
        return type(data.get("valid")) is not bool or not isinstance(status, str | None)
    if method == "autocomplete":
        return not isinstance(data.get("suggestions"), list)
    unit = data.get("unit")
    if unit is None:
        return type(data.get("found")) is not bool
    postcode = unit.get("postcode") if isinstance(unit, dict) else None
    full = isinstance(postcode, str) and COMPACT_POSTCODE.fullmatch(compact(postcode))
    return type(data.get("found")) is not bool or not full


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


def gives_result(method: str, reply: Reply | None) -> bool:
    """Tell whether a reply gives a result, not an error."""
    if reply is None or reply.status != HTTPStatus.OK:
        return False
    return not broken_body(method, reply.body)


def lookup_fields(call: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Return the lookup result that client.md builds from a call and a body."""
    address = data.get("administrative_address")
    recent = data.get("recent_house_address")
    return {
        "postcode": canonical(compact(call["code"])),
        "valid": data["valid"],
        "status": data.get("status"),
        "levelRequested": call.get("level", DEFAULT_LEVEL),
        "levelReceived": next(
            (level for field, level in LEVEL_FIELDS if field in data), DEFAULT_LEVEL
        ),
        "administrativeAddress": None
        if not isinstance(address, dict)
        else {name: address.get(field) for name, field in ADDRESS_FIELDS.items()},
        "recentHouseAddress": recent.get("recent") if isinstance(recent, dict) else None,
        "buildingUseStatus": data.get("building_use_status"),
    }


def reverse_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Return the reverse result that client.md builds from a body."""
    fields = {key: data.get(key) for key in ("found", "area", "district", "state")}
    fields["radiusM"] = data.get("radius_m")
    unit = data.get("unit")
    fields["unit"] = None
    if isinstance(unit, dict):
        confidence = unit.get("confidence")
        fields["unit"] = {
            "postcode": canonical(compact(unit["postcode"])),
            "distanceM": unit.get("distance_m"),
            "confidence": confidence if confidence in CONFIDENCES else "low",
            **{name: unit.get(field) for name, field in UNIT_NAMES.items()},
        }
    return fields


def autocomplete_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Return the parts of an autocomplete result that a body decides: segment, codes, labels."""
    return {
        "segment": data.get("segment"),
        "suggestions": [[item.get("code"), item.get("label")] for item in data["suggestions"]],
    }


def stated_fields(method: str, result: dict[str, Any], names: list[str]) -> dict[str, Any]:
    """Return the named fields of an expected result, in the form of the fields above."""
    fields = {name: result.get(name) for name in names}
    suggestions = fields.get("suggestions")
    if method == "autocomplete" and isinstance(suggestions, list):
        fields["suggestions"] = [[item.get("code"), item.get("label")] for item in suggestions]
    return fields


def result_problems(call: dict[str, Any], result: Any, body: dict[str, Any]) -> list[str]:
    """Return a line for each field of an expected result that the body does not give."""
    data, method = body["data"], call["method"]
    if method == "lookup":
        fields = lookup_fields(call, data)
    elif method == "reverse":
        fields = reverse_fields(data)
    else:
        fields = autocomplete_fields(data)
    stated = stated_fields(method, result if isinstance(result, dict) else {}, list(fields))
    return [
        f"The last response gives {name} {fields[name]!r}, not {stated[name]!r}."
        for name in fields
        if fields[name] != stated[name]
    ]


def outcome_truth(call: dict[str, Any], outcome: dict[str, Any], reply: Reply | None) -> list[str]:
    """Return the problems of the outcome of a call against the reply to its last attempt."""
    result = gives_result(call["method"], reply)
    if "error" in outcome and result:
        return ["The last response is a good 200, so the call has a result."]
    if "error" in outcome:
        expected = expected_error(reply)
        if outcome["error"] == expected:
            return []
        return [
            f"The last response gives {json.dumps(expected)}, not {json.dumps(outcome['error'])}."
        ]
    if reply is None or not result:
        if reply is not None and reply.status == HTTPStatus.OK:
            return [
                "The last response breaks client.md, so the call ends with unexpected_response."
            ]
        return [f"The last response gives the error {expected_error(reply)['code']}, not a result."]
    return result_problems(call, outcome["result"], reply.body)


def play(scenario: dict[str, Any], fixtures: dict[str, Any]) -> tuple[list[int], list[Played]]:
    """Play the calls of a scenario.

    Returns, for each call, the call that sent its request (itself, or an earlier call that it
    shares a request or a kept result with), and the played outcome of each call.
    """
    client, calls = scenario["client"], scenario["calls"]
    parallel = scenario.get("order") == "parallel"
    cache = client.get("cacheTtlMs", 0) > 0
    replies = [reply_of(response, fixtures) for response in scenario["responses"]]
    sent, leaders = 0, []
    played: list[Played] = []
    shared: dict[tuple[Any, ...], int] = {}
    for index, call in enumerate(calls):
        key = call_key(call)
        if key in shared:
            leaders.append(shared[key])
            played.append(played[shared[key]])
            continue
        outcome = Played(None, 0, [])
        if key is not None:
            outcome = play_call(call, client, replies, sent=sent)
        sent += outcome.attempts
        leaders.append(index)
        played.append(outcome)
        if key is not None and (
            parallel or (cache and gives_result(call["method"], outcome.reply))
        ):
            shared[key] = index
    return leaders, played


def fixture_method_problems(scenario: dict[str, Any], fixtures: dict[str, Any]) -> list[str]:
    """Return a problem for each fixture that answers another method than the calls use."""
    methods = {call["method"] for call in scenario["calls"]}
    allowed = {ERROR_SCHEMA, *(METHOD_SCHEMAS[method] for method in methods)}
    names = [response["fixture"] for response in scenario["responses"] if "fixture" in response]
    return [
        f"A {' or '.join(sorted(methods))} call cannot get {name}."
        for name in names
        if fixtures[name]["schema"] not in allowed
    ]


def count_problems(scenario: dict[str, Any], leaders: list[int], played: list[Played]) -> list[str]:
    """Return the problems of the attempts, the waits, the requests in flight and the request."""
    expect, calls = scenario["expect"], scenario["calls"]
    own = [outcome for index, outcome in enumerate(played) if leaders[index] == index]
    problems = []
    attempts = sum(outcome.attempts for outcome in own)
    if expect["attempts"] != attempts:
        problems.append(
            f"The responses and client.md give {attempts} attempts, not {expect['attempts']}."
        )
    waits = played[0].waits if len(calls) == 1 else []
    if waits and "waitsMs" not in expect:
        problems.append("A call that retries needs waitsMs.")
    if "waitsMs" in expect and expect["waitsMs"] != waits:
        problems.append(
            f"The responses and client.md give the waits {waits}, not {expect['waitsMs']}."
        )
    senders = [outcome for outcome in own if outcome.attempts]
    in_flight = min(MAX_IN_FLIGHT, len(senders)) if scenario.get("order") == "parallel" else 1
    if expect.get("maxInFlight", in_flight) != in_flight:
        problems.append(
            f"client.md gives {in_flight} requests in flight at most, not {expect['maxInFlight']}."
        )
    first = next((calls[i] for i, outcome in enumerate(played) if outcome.attempts), None)
    if "request" in expect and first is not None:
        request = expected_request(first, scenario["client"])
        if expect["request"] != request:
            problems.append(
                f"The first request is {json.dumps(request)}, not {json.dumps(expect['request'])}."
            )
    return problems


def truth_problems(scenario: dict[str, Any], fixtures: dict[str, Any]) -> list[str]:
    """Return the problems of a scenario whose expect part disagrees with client.md.

    The scenario must keep the format first.
    """
    problems = fixture_method_problems(scenario, fixtures)
    if problems:
        return problems
    leaders, played = play(scenario, fixtures)
    problems = count_problems(scenario, leaders, played)
    outcomes, calls = scenario["expect"]["outcomes"], scenario["calls"]
    for index, call in enumerate(calls):
        lead = leaders[index]
        if lead != index:
            if outcomes[index] != outcomes[lead]:
                problems.append(
                    f"Call {index + 1} gets the outcome of call {lead + 1}, "
                    "so the two must be the same."
                )
            continue
        found = outcome_truth(call, outcomes[index], played[index].reply)
        prefix = f"Call {index + 1}: " if len(calls) > 1 else ""
        problems += [prefix + problem for problem in found]
    return problems
