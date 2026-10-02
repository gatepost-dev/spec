# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Read the completed OpenAPI file, and check its paths, its evidence marks and its schemas.

Each check returns a list of problems, one line each. An empty list means that the file passes.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "openapi" / "gateway.completed.yaml"
EVIDENCE = ("observed", "documented", "assumed")
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
OPENAPI_URI = "urn:gatepost:openapi"

SchemaCheck = Callable[[str, object], list[str]]


def load_openapi(path: Path = OPENAPI) -> dict[str, Any]:
    """Return the completed OpenAPI file as a mapping."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise TypeError(f"{path.name} must hold a mapping.")
    return document


def responses(openapi: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield a label and the response object for each response of each operation.

    A response that refers to `components/responses` yields the component that it names.
    """
    shared = openapi.get("components", {}).get("responses", {})
    for path, operations in openapi["paths"].items():
        for method, operation in operations.items():
            for status, response in operation["responses"].items():
                reference = response.get("$ref", "")
                target = shared.get(reference.rpartition("/")[2], response)
                yield f"{method.upper()} {path} {status}", target


def openapi_problems(openapi: dict[str, Any]) -> list[str]:
    """Return the problems of the OpenAPI file: extra paths and missing evidence marks."""
    problems = [
        f"The path {path} is not a documented gateway path."
        for path in openapi["paths"]
        if path not in DOCUMENTED_PATHS
    ]
    for label, response in responses(openapi):
        if response.get("x-gatepost-evidence") not in EVIDENCE:
            problems.append(f"{label} needs x-gatepost-evidence: one of {', '.join(EVIDENCE)}.")
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
    for _, response in responses(openapi):
        for media in response.get("content", {}).values():
            names.add(media["schema"]["$ref"].rpartition("/")[2])
    return names
