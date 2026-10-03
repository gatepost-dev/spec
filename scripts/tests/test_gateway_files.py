# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for gateway_files: the OpenAPI file, fixtures and keys agree and stay synthetic."""

import copy
import tempfile
import unittest
from pathlib import Path
from typing import Any

import gateway_files

OPENAPI = gateway_files.load_openapi()
CHECK = gateway_files.schema_check(OPENAPI)
FIXTURES = gateway_files.load_fixtures()
KEYS = gateway_files.read_json(gateway_files.FIXTURES / "keys.json")


def marks(openapi: dict[str, Any]) -> dict[str, str]:
    return {
        f"{operation} {status}": response["x-gatepost-evidence"]
        for operation, status, response in gateway_files.responses(openapi)
    }


def edited_fixture(name: str, **fields: Any) -> dict[str, Any]:
    fixture: dict[str, Any] = copy.deepcopy(FIXTURES[name])
    fixture.update(fields)
    return fixture


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

    def test_rejects_an_evidence_value_that_is_not_a_mark(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        openapi["paths"]["/v1/lookup"]["get"]["responses"]["200"]["x-gatepost-evidence"] = "guess"
        [problem] = gateway_files.openapi_problems(openapi)
        self.assertTrue(problem.startswith("GET /v1/lookup 200 needs x-gatepost-evidence"))

    def test_reads_the_evidence_of_a_shared_response_from_its_component(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        del openapi["components"]["responses"]["BadRequest"]["x-gatepost-evidence"]
        labels = [problem.split(" needs")[0] for problem in gateway_files.openapi_problems(openapi)]
        self.assertIn("GET /v1/lookup 400", labels)
        self.assertIn("POST /v1/assembly/assemble 400", labels)

    def test_marks_as_observed_only_the_responses_that_a_call_returned(self) -> None:
        observed = sorted(label for label, mark in marks(OPENAPI).items() if mark == "observed")
        self.assertEqual(
            observed,
            [
                "GET /v1/assembly/disassemble 200",
                "GET /v1/lookup 200",
                "GET /v1/lookup 401",
                "GET /v1/lookup 403",
                "GET /v1/search/autocomplete 200",
                "GET /v1/search/autocomplete 401",
                "GET /v1/search/nearby 200",
                "GET /v1/search/reverse 200",
                "POST /v1/assembly/assemble 200",
            ],
        )

    def test_marks_as_observed_only_the_error_codes_that_a_call_returned(self) -> None:
        observed = sorted(
            f"{operation} {status} {code}"
            for operation, status, response in gateway_files.responses(OPENAPI)
            for code, mark in response.get("x-gatepost-error-codes", {}).items()
            if mark == "observed"
        )
        self.assertEqual(
            observed,
            [
                "GET /v1/lookup 401 auth_required",
                "GET /v1/lookup 403 level_not_granted",
                "GET /v1/search/autocomplete 401 auth_required",
            ],
        )

    def test_gives_each_error_code_of_a_response_its_own_mark(self) -> None:
        lookup = OPENAPI["paths"]["/v1/lookup"]["get"]["responses"]
        shared = OPENAPI["components"]["responses"]
        forbidden = shared[lookup["403"]["$ref"].rpartition("/")[2]]
        self.assertEqual(
            forbidden["x-gatepost-error-codes"],
            {
                "level_not_granted": "observed",
                "scope_not_granted": "assumed",
                "origin_not_allowed": "assumed",
            },
        )

    def test_rejects_error_codes_on_a_success(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        success = openapi["paths"]["/v1/lookup"]["get"]["responses"]["200"]
        success["x-gatepost-error-codes"] = {"not_found": "assumed"}
        self.assertEqual(
            gateway_files.openapi_problems(openapi),
            ["GET /v1/lookup 200 is a success and has no error codes."],
        )

    def test_rejects_an_error_response_with_no_error_codes(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        del openapi["components"]["responses"]["BadRequest"]["x-gatepost-error-codes"]
        problems = gateway_files.openapi_problems(openapi)
        self.assertIn("GET /v1/lookup 400 needs x-gatepost-error-codes.", problems)

    def test_rejects_an_error_code_that_claims_more_than_its_response(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        codes = openapi["components"]["responses"]["BadRequest"]["x-gatepost-error-codes"]
        codes["invalid_request"] = "observed"
        problems = gateway_files.openapi_problems(openapi)
        self.assertIn(
            "GET /v1/lookup 400 marks invalid_request observed, above its response (assumed).",
            problems,
        )

    def test_describes_the_answer_to_a_path_that_the_gateway_does_not_serve(self) -> None:
        [(status, response)] = [
            (status, response)
            for operation, status, response in gateway_files.responses(OPENAPI)
            if operation == "Any unknown path"
        ]
        self.assertEqual(status, "404")
        self.assertEqual(response["x-gatepost-error-codes"], {"not_found": "assumed"})

    def test_rejects_a_header_with_no_evidence_mark(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        del openapi["components"]["headers"]["RetryAfter"]["x-gatepost-evidence"]
        [problem] = gateway_files.openapi_problems(openapi)
        self.assertEqual(
            problem,
            "The header RetryAfter needs x-gatepost-evidence: "
            "one of observed, documented, assumed.",
        )

    def test_marks_the_retry_after_header_as_assumed(self) -> None:
        headers = OPENAPI["components"]["headers"]
        self.assertEqual(headers["RetryAfter"]["x-gatepost-evidence"], "assumed")
        self.assertEqual(headers["RateLimitLimit"]["x-gatepost-evidence"], "observed")

    def test_reads_a_path_item_with_shared_parameters(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        openapi["paths"]["/v1/lookup"]["parameters"] = []
        openapi["paths"]["/v1/lookup"]["summary"] = "Lookups"
        self.assertEqual(gateway_files.openapi_problems(openapi), [])

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


class FixtureTest(unittest.TestCase):
    def test_each_fixture_has_no_problem(self) -> None:
        for name, fixture in FIXTURES.items():
            with self.subTest(name):
                self.assertEqual(gateway_files.fixture_problems(name, fixture, CHECK), [])

    def test_each_fixture_matches_a_response_of_the_openapi_file(self) -> None:
        for name, fixture in FIXTURES.items():
            with self.subTest(name):
                self.assertEqual(
                    gateway_files.fixture_response_problems(name, fixture, OPENAPI), []
                )

    def test_rejects_a_status_that_no_response_with_the_schema_has(self) -> None:
        cases = {
            "errors/rate-limited": (200, "ErrorEnvelope"),
            "lookup/valid-level-1": (500, "LookupEnvelope"),
        }
        for name, (status, schema) in cases.items():
            with self.subTest(name):
                fixture = edited_fixture(name, status=status)
                [problem] = gateway_files.fixture_response_problems(name, fixture, OPENAPI)
                self.assertEqual(
                    problem,
                    f"Fixture {name}: no response with the schema {schema} "
                    f"has the status {status}.",
                )

    def test_rejects_an_error_code_that_the_status_does_not_carry(self) -> None:
        fixture = edited_fixture("errors/rate-limited")
        fixture["body"]["error"]["code"] = "banana"
        self.assertEqual(
            gateway_files.fixture_response_problems("errors/rate-limited", fixture, OPENAPI),
            [
                "Fixture errors/rate-limited: its name asks for the error code rate_limited.",
                "Fixture errors/rate-limited: no 429 response has the error code banana.",
            ],
        )

    def test_rejects_an_error_code_that_differs_from_the_file_name(self) -> None:
        fixture = edited_fixture("errors/level-not-granted-2")
        fixture["body"]["error"]["code"] = "scope_not_granted"
        name = "errors/level-not-granted-2"
        self.assertEqual(
            gateway_files.fixture_response_problems(name, fixture, OPENAPI),
            [f"Fixture {name}: its name asks for the error code level_not_granted."],
        )

    def test_rejects_evidence_that_claims_more_than_the_openapi_file(self) -> None:
        fixture = edited_fixture("errors/invalid-api-key", evidence="observed")
        self.assertEqual(
            gateway_files.fixture_response_problems("errors/invalid-api-key", fixture, OPENAPI),
            ["Fixture errors/invalid-api-key claims observed, but the OpenAPI file says assumed."],
        )

    def test_rejects_a_body_above_level_1_marked_as_observed(self) -> None:
        for name in ("lookup/valid-level-2", "lookup/valid-level-3"):
            with self.subTest(name):
                fixture = edited_fixture(name, evidence="observed")
                self.assertEqual(
                    gateway_files.fixture_response_problems(name, fixture, OPENAPI),
                    [f"Fixture {name} claims observed, but the OpenAPI file says documented."],
                )

    def test_skips_a_mark_that_is_not_valid_and_lets_the_file_check_name_it(self) -> None:
        openapi = copy.deepcopy(OPENAPI)
        openapi["paths"]["/v1/lookup"]["get"]["responses"]["200"]["x-gatepost-evidence"] = "guess"
        fixture = edited_fixture("lookup/valid-level-1")
        self.assertEqual(
            gateway_files.fixture_response_problems("lookup/valid-level-1", fixture, openapi), []
        )

    def test_accepts_a_status_in_a_range_of_the_openapi_file(self) -> None:
        fixture = edited_fixture("errors/rate-limited", status=503, evidence="assumed")
        fixture["body"]["error"]["code"] = "unavailable"
        self.assertEqual(
            gateway_files.fixture_response_problems("errors/unavailable", fixture, OPENAPI), []
        )

    def test_loads_a_fixture_in_a_deeper_folder_and_not_the_key_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "lookup" / "extra").mkdir(parents=True)
            (root / "lookup" / "extra" / "deep.json").write_text("{}", encoding="utf-8")
            (root / "keys.json").write_text("{}", encoding="utf-8")
            self.assertEqual(list(gateway_files.load_fixtures(root)), ["lookup/extra/deep"])

    def test_has_a_body_for_each_lookup_level_that_a_mock_key_holds(self) -> None:
        for level in (1, 2, 3):
            with self.subTest(level=level):
                self.assertIn(f"lookup/valid-level-{level}", FIXTURES)
                self.assertIn(f"errors/level-not-granted-{level}", FIXTURES)

    def test_rejects_a_body_that_does_not_match_its_schema(self) -> None:
        body = {"data": {"found": True, "coordinate": [7], "radius_m": 25}}
        fixture = edited_fixture("reverse/unit", body=body)
        self.assertEqual(
            gateway_files.fixture_problems("reverse/unit", fixture, CHECK),
            ["Fixture reverse/unit: [7] is too short at $.data.coordinate"],
        )

    def test_rejects_an_evidence_value_that_the_openapi_file_does_not_use(self) -> None:
        fixture = edited_fixture("nearby/empty", evidence="seen")
        [problem] = gateway_files.fixture_problems("nearby/empty", fixture, CHECK)
        self.assertEqual(
            problem, "Fixture nearby/empty needs evidence: one of observed, documented, assumed."
        )

    def test_rejects_a_status_that_is_not_an_integer(self) -> None:
        fixture = edited_fixture("nearby/empty", status="200")
        self.assertEqual(
            gateway_files.fixture_problems("nearby/empty", fixture, CHECK),
            ["Fixture nearby/empty needs an integer status."],
        )

    def test_rejects_a_fixture_with_a_field_missing(self) -> None:
        fixture = edited_fixture("nearby/empty")
        del fixture["evidence"]
        [problem] = gateway_files.fixture_problems("nearby/empty", fixture, CHECK)
        self.assertTrue(problem.startswith("Fixture nearby/empty must have the fields version,"))


class KeysTest(unittest.TestCase):
    def test_the_key_file_has_no_problem(self) -> None:
        self.assertEqual(gateway_files.key_problems(KEYS), [])

    def test_rejects_a_key_that_could_be_real(self) -> None:
        keys = copy.deepcopy(KEYS)
        keys["keys"][0]["key"] = "nipost_test_a1b2c3d4e5"
        self.assertEqual(
            gateway_files.key_problems(keys),
            ["The key nipost_test_a1b2c3d4e5 must be unique and start with a mock prefix."],
        )

    def test_rejects_a_key_twice(self) -> None:
        keys = copy.deepcopy(KEYS)
        keys["keys"].append(copy.deepcopy(keys["keys"][0]))
        self.assertEqual(len(gateway_files.key_problems(keys)), 1)

    def test_rejects_a_level_that_no_key_can_hold(self) -> None:
        keys = copy.deepcopy(KEYS)
        keys["keys"][0]["lookupLevel"] = 4
        self.assertEqual(
            gateway_files.key_problems(keys),
            ["The key nipost_test_mock_l1 needs a lookupLevel from 1 to 3."],
        )


class SyntheticPostcodeTest(unittest.TestCase):
    def test_finds_a_real_postcode_in_each_form_and_case(self) -> None:
        text = "EK-01-A03-FK-01, EK 01 A03 FK 01, ek01a03fk01 and FC-01-Z99-ZZ-01"
        self.assertEqual(
            gateway_files.real_postcodes(text),
            ["EK-01-A03-FK-01", "EK 01 A03 FK 01", "ek01a03fk01"],
        )

    def test_finds_a_postcode_with_other_separators(self) -> None:
        text = "EK/01/A03/FK/01, EK_01_A03_FK_01 and EK.01.A03.FK.01"
        self.assertEqual(
            gateway_files.real_postcodes(text),
            ["EK/01/A03/FK/01", "EK_01_A03_FK_01", "EK.01.A03.FK.01"],
        )

    def test_finds_a_synthetic_district_in_a_state_other_than_fc(self) -> None:
        self.assertEqual(gateway_files.real_postcodes("LA-01-Z99-ZZ-01"), ["LA-01-Z99-ZZ-01"])

    def test_keeps_a_partial_postcode_and_a_longer_word(self) -> None:
        self.assertEqual(gateway_files.real_postcodes("EK-01-A03 and XEK01A03FK01"), [])

    def test_names_the_file_that_holds_a_real_postcode(self) -> None:
        with tempfile.TemporaryDirectory(dir=gateway_files.ROOT) as folder:
            path = Path(folder) / "probe.json"
            path.write_text('{"postcode": "LA-12-Z98-IV-95"}', encoding="utf-8")
            [problem] = gateway_files.postcode_problems([path])
        self.assertTrue(
            problem.endswith("probe.json holds the postcode LA-12-Z98-IV-95. Use a synthetic code.")
        )


class KeyTextTest(unittest.TestCase):
    def test_names_the_file_that_holds_text_in_the_form_of_a_real_key(self) -> None:
        with tempfile.TemporaryDirectory(dir=gateway_files.ROOT) as folder:
            path = Path(folder) / "probe.json"
            path.write_text(
                '{"message": "nipost_live_a1b2c3d4e5f6a7b8", "key": "nipost_test_mock_l1"}',
                encoding="utf-8",
            )
            [problem] = gateway_files.key_text_problems([path])
        self.assertTrue(
            problem.endswith(
                "probe.json holds the key nipost_live_a1b2c3d4e5f6a7b8. Use a mock key."
            )
        )

    def test_keeps_the_prefixes_that_the_docs_name(self) -> None:
        with tempfile.TemporaryDirectory(dir=gateway_files.ROOT) as folder:
            path = Path(folder) / "probe.md"
            path.write_text("A key starts with nipost_test_ or nipost_pk_live_.", encoding="utf-8")
            self.assertEqual(gateway_files.key_text_problems([path]), [])
