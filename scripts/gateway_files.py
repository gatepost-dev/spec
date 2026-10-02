# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Read the completed OpenAPI file, the fixtures and the mock keys, and check that they agree.

Each check returns a list of problems, one line each. An empty list means that the file passes.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "openapi" / "gateway.completed.yaml"
FIXTURES = ROOT / "fixtures"
# The marks, from the strongest claim to the weakest.
EVIDENCE = ("observed", "documented", "assumed")
MARKS = ", ".join(EVIDENCE)
EVIDENCE_MARK = "x-gatepost-evidence"
ERROR_CODES = "x-gatepost-error-codes"
# The gateway answers a path that it does not serve. This key of the file describes that answer.
UNKNOWN_PATH = "x-gatepost-unknown-path"
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
# NIPOST documents these gateway paths. SEC-4 lets a client call no other path.
DOCUMENTED_PATHS = (
    "/healthz",
    "/v1/lookup",
    "/v1/search/reverse",
    "/v1/search/nearby",
    "/v1/search/autocomplete",
    "/v1/assembly/assemble",
    "/v1/assembly/disassemble",
)
FIXTURE_FIELDS = ("version", "description", "evidence", "schema", "status", "body")
KEY_FIELDS = ("key", "kind", "lookupLevel", "lookupScope", "credits", "rateLimited", "origins")
# A mock key must never look like a real key, so a real key cannot slip into the table.
MOCK_KEY = re.compile(r"nipost_(?:pk_)?test_mock(?:_[a-z0-9]+)*")
# Five segments, with or without separators, in either letter case.
POSTCODE = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z]{2})[- ]?([0-9]{2})[- ]?([A-Za-z0-9]{3})[- ]?([A-Za-z]{2})"
    r"[- ]?([0-9]{2})(?![A-Za-z0-9])"
)
OPENAPI_URI = "urn:gatepost:openapi"

SchemaCheck = Callable[[str, object], list[str]]


def read_json(path: Path) -> Any:
    """Return the JSON value in a file."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_openapi(path: Path = OPENAPI) -> dict[str, Any]:
    """Return the completed OpenAPI file as a mapping."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise TypeError(f"{path.name} must hold a mapping.")
    return document


def operations(openapi: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield a label and each operation, then the answer to a path that the file does not list.

    A path item can also hold keys that are not methods, such as `parameters`. They are skipped.
    """
    for path, item in openapi["paths"].items():
        for method in HTTP_METHODS:
            if method in item:
                yield f"{method.upper()} {path}", item[method]
    yield "Any unknown path", openapi[UNKNOWN_PATH]


def responses(openapi: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Yield the operation's label, the status and the response object of each response.

    A response that refers to `components/responses` yields the component that it names.
    """
    shared = openapi.get("components", {}).get("responses", {})
    for label, operation in operations(openapi):
        for status, response in operation["responses"].items():
            reference = response.get("$ref", "")
            yield label, status, shared.get(reference.rpartition("/")[2], response)


def code_problems(label: str, status: str, response: dict[str, Any]) -> list[str]:
    """Return the problems of the error codes of one response.

    An error response names each code that it can carry, and gives each code its own mark. A
    code can claim no more than its response: a code is not observed in a response that no call
    returned.
    """
    codes = response.get(ERROR_CODES)
    if status.startswith("2"):
        return [] if codes is None else [f"{label} {status} is a success and has no error codes."]
    if not isinstance(codes, dict) or not codes:
        return [f"{label} {status} needs {ERROR_CODES}."]
    ceiling = response[EVIDENCE_MARK]
    problems = []
    for code, mark in codes.items():
        if mark not in EVIDENCE:
            problems.append(f"{label} {status} needs a mark for {code}: one of {MARKS}.")
        elif EVIDENCE.index(mark) < EVIDENCE.index(ceiling):
            problems.append(
                f"{label} {status} marks {code} {mark}, above its response ({ceiling})."
            )
    return problems


def openapi_problems(openapi: dict[str, Any]) -> list[str]:
    """Return the problems of the OpenAPI file: extra paths, and missing or excessive marks."""
    problems = [
        f"The path {path} is not a documented gateway path."
        for path in openapi["paths"]
        if path not in DOCUMENTED_PATHS
    ]
    problems += [
        f"The header {name} needs {EVIDENCE_MARK}: one of {MARKS}."
        for name, header in openapi["components"]["headers"].items()
        if header.get(EVIDENCE_MARK) not in EVIDENCE
    ]
    for label, status, response in responses(openapi):
        if response.get(EVIDENCE_MARK) not in EVIDENCE:
            problems.append(f"{label} {status} needs {EVIDENCE_MARK}: one of {MARKS}.")
            continue
        problems += code_problems(label, status, response)
    return problems


def schema_check(openapi: dict[str, Any]) -> SchemaCheck:
    """Return a function that checks a value against a schema of the OpenAPI file.

    The function takes a name in `components/schemas` and a value, and returns the problems.
    """
    resource = Resource.from_contents(openapi, default_specification=DRAFT202012)
    registry: Registry[Any] = Registry().with_resource(OPENAPI_URI, resource)
    known = openapi["components"]["schemas"]

    def check(name: str, value: object) -> list[str]:
        if name not in known:
            return [f"The OpenAPI file has no schema {name}."]
        schema = {"$ref": f"{OPENAPI_URI}#/components/schemas/{name}"}
        validator = Draft202012Validator(schema, registry=registry)
        return [
            f"{error.message} at {error.json_path}"
            for error in sorted(validator.iter_errors(value), key=str)
        ]

    return check


def schemas_in_responses(openapi: dict[str, Any]) -> set[str]:
    """Return the names of the schemas that the responses use directly."""
    names = set()
    for _, _, response in responses(openapi):
        for media in response.get("content", {}).values():
            names.add(media["schema"]["$ref"].rpartition("/")[2])
    return names


def load_fixtures(root: Path = FIXTURES) -> dict[str, Any]:
    """Return each fixture by its name, the path under the folder without `.json`."""
    return {
        path.relative_to(root).with_suffix("").as_posix(): read_json(path)
        for path in sorted(root.glob("*/*.json"))
    }


def fixture_problems(name: str, fixture: Any, check: SchemaCheck) -> list[str]:
    """Return the problems of one fixture, including a body that does not match its schema."""
    if not isinstance(fixture, dict) or tuple(fixture) != FIXTURE_FIELDS:
        return [f"Fixture {name} must have the fields {', '.join(FIXTURE_FIELDS)}."]
    problems = []
    if fixture["version"] != 1:
        problems.append(f"Fixture {name} must have version 1.")
    if fixture["evidence"] not in EVIDENCE:
        problems.append(f"Fixture {name} needs evidence: one of {MARKS}.")
    if type(fixture["status"]) is not int:
        problems.append(f"Fixture {name} needs an integer status.")
    problems += [
        f"Fixture {name}: {message}" for message in check(fixture["schema"], fixture["body"])
    ]
    return problems


def key_problems(document: Any) -> list[str]:
    """Return the problems of `fixtures/keys.json`."""
    problems = []
    keys = document.get("keys", []) if isinstance(document, dict) else []
    if not keys or document.get("version") != 1:
        problems.append("keys.json must have version 1 and a list of keys.")
    seen = set()
    for entry in keys:
        if not isinstance(entry, dict) or tuple(entry) != KEY_FIELDS:
            problems.append(f"Each key must have the fields {', '.join(KEY_FIELDS)}.")
            continue
        key = entry["key"]
        if key in seen or not MOCK_KEY.fullmatch(key):
            problems.append(f"The key {key} must be unique and start with a mock prefix.")
        seen.add(key)
        if entry["lookupLevel"] not in (1, 2, 3):
            problems.append(f"The key {key} needs a lookupLevel from 1 to 3.")
    return problems


def real_postcodes(text: str) -> list[str]:
    """Return each full postcode in the text that is not synthetic.

    A synthetic postcode has the district Z99 and the area ZZ.
    """
    return [
        match.group(0)
        for match in POSTCODE.finditer(text)
        if (match.group(3).upper(), match.group(4).upper()) != ("Z99", "ZZ")
    ]


def postcode_problems(paths: list[Path]) -> list[str]:
    """Return a problem for each postcode in the files that is not synthetic."""
    return [
        f"{path.relative_to(ROOT)} holds the postcode {code}. Use a synthetic code."
        for path in paths
        for code in real_postcodes(path.read_text(encoding="utf-8"))
    ]
