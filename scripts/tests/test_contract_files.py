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

SCENARIOS = contract_files.load_scenarios()
FIXTURE_NAMES = set(gateway_files.load_fixtures())
CODES = contract_files.error_codes()
STANDARDS = gateway_files.ROOT / "standards" / "CODING_STANDARDS.md"


def problems_of(name: str, edit: Any) -> list[str]:
    scenario = copy.deepcopy(SCENARIOS[name])
    edit(scenario)
    return contract_files.scenario_problems(name, scenario, FIXTURE_NAMES, CODES)


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
                    contract_files.scenario_problems(name, scenario, FIXTURE_NAMES, CODES), []
                )

    def test_the_scenarios_cover_each_error_code_and_each_required_rule(self) -> None:
        self.assertEqual(contract_files.coverage_problems(SCENARIOS, CODES), [])

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
            ["lookup-level-1: A lookup call needs code, level, and nothing else."],
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


class CoverageTest(unittest.TestCase):
    def test_reports_an_error_code_that_no_scenario_reaches(self) -> None:
        scenarios = {
            name: scenario
            for name, scenario in SCENARIOS.items()
            if name != "lookup-origin-not-allowed"
        }
        self.assertEqual(
            contract_files.coverage_problems(scenarios, CODES),
            ["No scenario ends with the error code origin_not_allowed."],
        )

    def test_reports_a_required_scenario_that_is_missing(self) -> None:
        scenarios = {
            name: scenario for name, scenario in SCENARIOS.items() if name != "lookup-queue-limit"
        }
        self.assertEqual(
            contract_files.coverage_problems(scenarios, CODES),
            ["The scenario lookup-queue-limit is missing."],
        )
