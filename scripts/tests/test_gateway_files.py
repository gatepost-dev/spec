# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for gateway_files: the OpenAPI file has the documented paths, evidence and schemas."""

import copy
import unittest

import gateway_files

OPENAPI = gateway_files.load_openapi()
CHECK = gateway_files.schema_check(OPENAPI)


class OpenApiTest(unittest.TestCase):
    def test_the_file_has_no_problem(self) -> None:
        self.assertEqual(gateway_files.openapi_problems(OPENAPI), [])

    def test_lists_each_documented_gateway_path_and_no_other(self) -> None:
        self.assertEqual(sorted(OPENAPI["paths"]), sorted(gateway_files.DOCUMENTED_PATHS))

    def test_rejects_a_path_that_nipost_does_not_document(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        openapi["paths"]["/v1/widget/lookup"] = openapi["paths"]["/v1/lookup"]
        self.assertEqual(
            gateway_files.openapi_problems(openapi),
            ["The path /v1/widget/lookup is not a documented gateway path."],
        )

    def test_rejects_a_response_with_no_evidence_mark(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        del openapi["paths"]["/v1/lookup"]["get"]["responses"]["200"]["x-gatepost-evidence"]
        [problem] = gateway_files.openapi_problems(openapi)
        self.assertTrue(problem.startswith("GET /v1/lookup 200 needs x-gatepost-evidence"))

    def test_reads_the_evidence_of_a_shared_response_from_its_component(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        del openapi["components"]["responses"]["Unauthorized"]["x-gatepost-evidence"]
        labels = [problem.split(" needs")[0] for problem in gateway_files.openapi_problems(openapi)]
        self.assertIn("GET /v1/lookup 401", labels)
        self.assertIn("POST /v1/assembly/assemble 401", labels)

    def test_marks_each_lookup_above_level_1_as_not_observed(self) -> None:
        schemas = OPENAPI["components"]["schemas"]
        for name in ("AdministrativeAddress", "RecentHouseAddress"):
            with self.subTest(name):
                self.assertIn("Documented, not observed.", schemas[name]["description"])
        building_use = schemas["Lookup"]["properties"]["building_use_status"]
        self.assertIn("Documented, not observed.", building_use["description"])


class SchemaCheckTest(unittest.TestCase):
    def test_names_the_missing_field_and_its_place(self) -> None:
        self.assertEqual(
            CHECK("Segments", {"state": "FC"}),
            [
                "'area' is a required property at $",
                "'district' is a required property at $",
                "'lga' is a required property at $",
                "'unit' is a required property at $",
            ],
        )

    def test_follows_references_between_schemas(self) -> None:
        body = {"data": {"postcode": "FC-01-Z99-ZZ-01", "valid": "yes"}}
        self.assertEqual(
            CHECK("LookupEnvelope", body), ["'yes' is not of type 'boolean' at $.data.valid"]
        )

    def test_rejects_a_schema_name_that_the_file_does_not_have(self) -> None:
        self.assertEqual(CHECK("Lookups", {}), ["The OpenAPI file has no schema Lookups."])
