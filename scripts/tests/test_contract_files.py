# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for contract_files: each scenario keeps the format, and together they cover client.md."""

import copy
import tempfile
import unittest
from pathlib import Path
from typing import Any

import contract_files
import gateway_files
import scenario_truth

SCENARIOS = contract_files.load_scenarios()
FIXTURES = gateway_files.load_fixtures()
CODES = contract_files.error_codes()
CLIENT = contract_files.CLIENT_DOC.read_text(encoding="utf-8")
STANDARDS = gateway_files.ROOT / "standards" / "CODING_STANDARDS.md"
FILES = contract_files.synthetic_files()


def problems_of(name: str, edit: Any) -> list[str]:
    scenario = copy.deepcopy(SCENARIOS[name])
    edit(scenario)
    return contract_files.scenario_problems(name, scenario, FIXTURES, CODES)


def without(name: str) -> dict[str, Any]:
    return {other: scenario for other, scenario in SCENARIOS.items() if other != name}


def error_row(condition: str) -> str:
    return next(line for line in CLIENT.splitlines() if line.startswith(f"| {condition} |"))


class ClientDocTest(unittest.TestCase):
    def test_lists_the_error_codes_of_the_design_in_the_order_of_the_map(self) -> None:
        self.assertEqual(
            CODES,
            [
                "invalid_input",
                "unauthorized",
                "insufficient_credits",
                "origin_not_allowed",
                "forbidden",
                "rate_limited",
                "server_error",
                "unexpected_response",
                "network_error",
                "timeout",
            ],
        )

    def test_the_standards_send_the_status_map_to_client_md(self) -> None:
        err_1 = next(
            line for line in STANDARDS.read_text(encoding="utf-8").splitlines() if "**ERR-1" in line
        )
        self.assertIn("`spec/client.md`", err_1)

    def test_reads_the_rows_of_the_error_table_and_no_other_table(self) -> None:
        text = (
            "# Client\n\n## Errors\n\n| a | `x_code` | no |\n\n"
            "## Retries\n\n| b | `y_code` | yes |\n"
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "client.md"
            path.write_text(text, encoding="utf-8")
            self.assertEqual(contract_files.error_codes(path), ["x_code"])


class ScenarioFileTest(unittest.TestCase):
    def test_each_scenario_has_no_problem(self) -> None:
        for name, scenario in SCENARIOS.items():
            with self.subTest(name):
                self.assertEqual(
                    contract_files.scenario_problems(name, scenario, FIXTURES, CODES), []
                )

    def test_the_scenarios_cover_each_error_code_and_each_required_rule(self) -> None:
        self.assertEqual(contract_files.coverage_problems(SCENARIOS, CLIENT), [])

    def test_the_whole_check_finds_no_problem(self) -> None:
        self.assertEqual(contract_files.all_problems(), [])


class ScenarioProblemTest(unittest.TestCase):
    def test_rejects_an_id_that_differs_from_the_file_name(self) -> None:
        self.assertEqual(
            problems_of("lookup-level-1", lambda scenario: scenario.update(id="lookup-level-one")),
            ["lookup-level-1: The version must be 1, and the id must equal the file name."],
        )

    def test_rejects_a_fixture_that_does_not_exist(self) -> None:
        def rename(scenario: dict[str, Any]) -> None:
            scenario["responses"][0]["fixture"] = "lookup/valid-level-9"

        self.assertEqual(
            problems_of("lookup-level-1", rename),
            ["lookup-level-1: No fixture is named lookup/valid-level-9."],
        )

    def test_rejects_a_response_with_two_kinds(self) -> None:
        def add_drop(scenario: dict[str, Any]) -> None:
            scenario["responses"][0]["drop"] = True

        [problem] = problems_of("lookup-level-1", add_drop)
        self.assertIn("needs exactly one of body, text, fixture, hang, drop", problem)

    def test_rejects_a_status_beside_a_fixture(self) -> None:
        def add_status(scenario: dict[str, Any]) -> None:
            scenario["responses"][0]["status"] = 200

        self.assertEqual(
            problems_of("lookup-level-1", add_status),
            ["lookup-level-1: A fixture response must not have a status."],
        )

    def test_rejects_a_body_with_no_status(self) -> None:
        def drop_status(scenario: dict[str, Any]) -> None:
            del scenario["responses"][0]["status"]

        self.assertEqual(
            problems_of("lookup-server-error", drop_status),
            ["lookup-server-error: A body response needs an integer status."],
        )

    def test_rejects_an_error_code_that_client_md_does_not_list(self) -> None:
        def rename(scenario: dict[str, Any]) -> None:
            scenario["expect"]["outcomes"][0]["error"]["code"] = "bad_gateway"

        self.assertEqual(
            problems_of("lookup-server-error", rename),
            ["lookup-server-error: The error code bad_gateway is not in client.md."],
        )

    def test_rejects_a_missing_outcome(self) -> None:
        def drop_outcome(scenario: dict[str, Any]) -> None:
            scenario["expect"]["outcomes"].pop()

        self.assertEqual(
            problems_of("lookup-shared-request", drop_outcome),
            ["lookup-shared-request: expect needs one outcome for each call."],
        )

    def test_rejects_waits_that_do_not_fit_the_attempts(self) -> None:
        def add_wait(scenario: dict[str, Any]) -> None:
            scenario["expect"]["waitsMs"].append({"min": 2000, "max": 2250})

        self.assertEqual(
            problems_of("lookup-retry-503", add_wait),
            ["lookup-retry-503: waitsMs needs one call, and one wait less than the attempts."],
        )

    def test_rejects_two_calls_with_no_order(self) -> None:
        self.assertEqual(
            problems_of("lookup-shared-request", lambda scenario: scenario.pop("order")),
            ["lookup-shared-request: Two or more calls need an order: parallel, sequential."],
        )

    def test_rejects_a_call_with_a_field_of_another_method(self) -> None:
        def add_field(scenario: dict[str, Any]) -> None:
            scenario["calls"][0]["q"] = "F"

        self.assertEqual(
            problems_of("lookup-level-1", add_field),
            ["lookup-level-1: A lookup call needs code and can hold level, and nothing else."],
        )

    def test_rejects_a_client_option_that_client_md_does_not_name(self) -> None:
        self.assertEqual(
            problems_of("lookup-level-1", lambda scenario: scenario["client"].update(retries=1)),
            ["lookup-level-1: client can hold only apiKey, timeoutMs, maxRetries, cacheTtlMs."],
        )

    def test_rejects_an_attempt_with_no_response(self) -> None:
        self.assertEqual(
            problems_of("lookup-level-1", lambda scenario: scenario.update(responses=[])),
            ["lookup-level-1: No attempt means no response, and the other way round."],
        )

    def test_accepts_a_lookup_call_with_no_level(self) -> None:
        self.assertEqual(problems_of("lookup-level-1", lambda s: s["calls"][0].pop("level")), [])

    def test_names_a_field_of_the_wrong_type_instead_of_failing(self) -> None:
        def name_a_list(scenario: dict[str, Any]) -> None:
            scenario["responses"][0]["fixture"] = ["lookup/valid-level-1"]

        cases = {
            "calls": (lambda s: s.update(calls=None), "calls must be a list."),
            "outcomes": (
                lambda s: s["expect"].update(outcomes=5),
                "expect needs attempts and a list of outcomes.",
            ),
            "fixture": (name_a_list, "No fixture is named ['lookup/valid-level-1']."),
        }
        for field, (edit, problem) in cases.items():
            with self.subTest(field):
                self.assertEqual(
                    problems_of("lookup-level-1", edit), [f"lookup-level-1: {problem}"]
                )


class ScenarioTruthTest(unittest.TestCase):
    def test_rejects_an_error_code_that_the_last_response_does_not_give(self) -> None:
        def say_forbidden(scenario: dict[str, Any]) -> None:
            scenario["expect"]["outcomes"][0]["error"]["code"] = "forbidden"

        [problem] = problems_of("lookup-bad-request", say_forbidden)
        self.assertTrue(
            problem.startswith(
                'lookup-bad-request: The last response gives {"code": "invalid_input", '
            )
        )

    def test_rejects_a_status_that_the_last_response_does_not_have(self) -> None:
        def say_200(scenario: dict[str, Any]) -> None:
            scenario["expect"]["outcomes"][0]["error"]["status"] = 200

        [problem] = problems_of("lookup-server-error", say_200)
        self.assertIn('"status": 500', problem)

    def test_rejects_a_result_that_the_fixture_does_not_give(self) -> None:
        def send_level_3(scenario: dict[str, Any]) -> None:
            scenario["responses"][0]["fixture"] = "lookup/valid-level-3"

        problems = problems_of("lookup-level-1", send_level_3)
        self.assertIn("lookup-level-1: The last response gives status None, not 'valid'.", problems)
        self.assertIn("lookup-level-1: The last response gives levelReceived 3, not 1.", problems)

    def test_rejects_a_fixture_of_another_method(self) -> None:
        def send_reverse(scenario: dict[str, Any]) -> None:
            scenario["responses"][0]["fixture"] = "reverse/unit"

        problems = problems_of("lookup-level-1", send_reverse)
        self.assertEqual(problems[0], "lookup-level-1: A lookup call cannot get reverse/unit.")

    def test_rejects_more_attempts_than_the_responses_give(self) -> None:
        self.assertEqual(
            problems_of("lookup-level-1", lambda s: s["expect"].update(attempts=4)),
            ["lookup-level-1: The responses and client.md give 1 attempts, not 4."],
        )

    def test_rejects_a_code_that_does_not_fit_its_status_when_calls_share_responses(self) -> None:
        def say_forbidden(scenario: dict[str, Any]) -> None:
            scenario["expect"]["outcomes"][0]["error"]["code"] = "forbidden"

        [problem] = problems_of("lookup-error-not-cached", say_forbidden)
        self.assertTrue(
            problem.startswith(
                'lookup-error-not-cached: Call 1: The last response gives {"code": "invalid_input"'
            )
        )

    def test_reads_the_retry_after_of_the_last_response(self) -> None:
        def drop_wait(scenario: dict[str, Any]) -> None:
            scenario["expect"]["outcomes"][0]["error"]["retryAfterMs"] = None

        [problem] = problems_of("lookup-retry-after-too-long", drop_wait)
        self.assertIn('"retryAfterMs": 120000', problem)


class StatusMapTest(unittest.TestCase):
    def test_maps_each_status_as_the_error_table_of_client_md_does(self) -> None:
        samples: dict[str, list[tuple[int, str | None]]] = {
            "status 401": [(401, "auth_required")],
            "status 402": [(402, "insufficient_credits")],
            "status 403, with the API code `origin_not_allowed`": [(403, "origin_not_allowed")],
            "status 403, with any other API code": [(403, "level_not_granted"), (403, None)],
            "status 429": [(429, "rate_limited")],
            "status 502, 503 or 504": [(502, None), (503, "unavailable"), (504, None)],
            "any other status from 400 to 499": [(400, None), (404, "not_found"), (499, None)],
            "any other status that is not 200": [(500, "internal"), (501, None), (302, None)],
        }
        rows = [row for row in contract_files.error_rows(CLIENT) if "status" in row.condition]
        self.assertEqual(
            [row.condition for row in rows if not row.condition.startswith("status 200")],
            list(samples),
        )
        for row in rows:
            for status, api_code in samples.get(row.condition, [(200, None)]):
                with self.subTest(status=status, api_code=api_code):
                    self.assertEqual(scenario_truth.error_code(status, api_code), row.code)


class CoverageTest(unittest.TestCase):
    def test_reports_each_scenario_that_is_deleted(self) -> None:
        for name in SCENARIOS:
            with self.subTest(name):
                self.assertIn(
                    f"client.md names the scenario {name}, which has no file.",
                    contract_files.coverage_problems(without(name), CLIENT),
                )

    def test_reports_a_scenario_that_client_md_does_not_name(self) -> None:
        scenarios = {**SCENARIOS, "lookup-level-one": SCENARIOS["lookup-level-1"]}
        self.assertEqual(
            contract_files.coverage_problems(scenarios, CLIENT),
            ["client.md names no rule for the scenario lookup-level-one."],
        )

    def test_reports_an_error_row_with_no_scenario(self) -> None:
        row = error_row("status 402")
        text = CLIENT.replace(row, row.replace("`lookup-insufficient-credits`", ""))
        self.assertEqual(
            contract_files.coverage_problems(without("lookup-insufficient-credits"), text),
            ["The error row status 402 in client.md names no scenario."],
        )

    def test_reports_a_scenario_of_a_row_that_ends_with_another_code(self) -> None:
        row = error_row("status 402")
        text = CLIENT.replace(row, f"{row} `lookup-no-key` |")
        self.assertEqual(
            contract_files.coverage_problems(SCENARIOS, text),
            ["The scenario lookup-no-key does not end with insufficient_credits, as its row says."],
        )

    def test_reads_the_scenarios_of_each_error_row(self) -> None:
        rows = {row.condition: row for row in contract_files.error_rows(CLIENT)}
        self.assertEqual(rows["status 429"].code, "rate_limited")
        self.assertIn("lookup-rate-limited", rows["status 429"].scenarios)


class SyntheticFilesTest(unittest.TestCase):
    def test_scans_the_fixtures_the_scenarios_and_the_docs_beside_them(self) -> None:
        names = {path.relative_to(gateway_files.ROOT).as_posix() for path in FILES}
        for name in (
            "client.md",
            "contract/README.md",
            "contract/lookup-level-1.json",
            "fixtures/README.md",
            "fixtures/keys.json",
            "fixtures/lookup/valid-level-1.json",
            "openapi/gateway.completed.yaml",
        ):
            self.assertIn(name, names)

    def test_finds_no_real_postcode_and_no_real_key_in_them(self) -> None:
        self.assertEqual(gateway_files.postcode_problems(FILES), [])
        self.assertEqual(gateway_files.key_text_problems(FILES), [])
