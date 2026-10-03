# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for scenario_truth: a scenario's outcome, attempts, waits and request follow client.md."""

import copy
import unittest
from typing import Any

import contract_files
import gateway_files
import scenario_truth

SCENARIOS = contract_files.load_scenarios()
FIXTURES = gateway_files.load_fixtures()
CODES = contract_files.error_codes()


def problems_of(name: str, edit: Any) -> list[str]:
    scenario = copy.deepcopy(SCENARIOS[name])
    edit(scenario)
    return contract_files.scenario_problems(name, scenario, FIXTURES, CODES)


def set_expect(**fields: Any) -> Any:
    return lambda scenario: scenario["expect"].update(fields)


class OutcomeTest(unittest.TestCase):
    def test_rejects_an_error_for_a_good_200_body(self) -> None:
        error = {"code": "unexpected_response", "status": 200, "apiCode": None}
        edit = set_expect(outcomes=[{"error": {**error, "retryAfterMs": None}}])
        self.assertEqual(
            problems_of("lookup-unknown-fields", edit),
            ["lookup-unknown-fields: The last response is a good 200, so the call has a result."],
        )

    def test_rejects_a_result_for_a_200_body_that_breaks_client_md(self) -> None:
        result = SCENARIOS["lookup-level-1"]["expect"]["outcomes"][0]
        self.assertEqual(
            problems_of("lookup-missing-valid", set_expect(outcomes=[result])),
            [
                "lookup-missing-valid: The last response breaks client.md, "
                "so the call ends with unexpected_response."
            ],
        )

    def test_rejects_an_address_that_the_body_does_not_hold(self) -> None:
        def rename(scenario: dict[str, Any]) -> None:
            outcome = scenario["expect"]["outcomes"][0]["result"]
            outcome["administrativeAddress"]["lgaName"] = "OTHER LGA"

        [problem] = problems_of("lookup-level-2", rename)
        self.assertTrue(problem.startswith("lookup-level-2: The last response gives administr"))

    def test_rejects_a_postcode_that_is_not_the_callers(self) -> None:
        def take_echo(scenario: dict[str, Any]) -> None:
            scenario["expect"]["outcomes"][0]["result"]["postcode"] = "HELLO"

        self.assertEqual(
            problems_of("lookup-echo-ignored", take_echo),
            [
                "lookup-echo-ignored: The last response gives postcode "
                "'FC-01-Z99-ZZ-01', not 'HELLO'."
            ],
        )

    def test_rejects_a_suggestion_postcode_that_the_typed_text_does_not_give(self) -> None:
        def move_postcode(scenario: dict[str, Any]) -> None:
            suggestions = scenario["expect"]["outcomes"][0]["result"]["suggestions"]
            suggestions[0]["postcode"] = "FC-01-ZZZ"

        [problem] = problems_of("autocomplete-district", move_postcode)
        self.assertTrue(problem.startswith("autocomplete-district: The last response gives sugg"))

    def test_rejects_a_shared_call_with_another_outcome(self) -> None:
        def change_second(scenario: dict[str, Any]) -> None:
            scenario["expect"]["outcomes"][1]["result"]["valid"] = False

        self.assertEqual(
            problems_of("lookup-cache-hit", change_second),
            ["lookup-cache-hit: Call 2 gets the outcome of call 1, so the two must be the same."],
        )


class AttemptTest(unittest.TestCase):
    def test_counts_the_attempts_of_each_scenario_in_the_review(self) -> None:
        cases = {
            "lookup-cache-hit": (2, 1),
            "lookup-shared-request": (2, 1),
            "autocomplete-timeout": (3, 1),
            "lookup-deadline": (2, 1),
        }
        for name, (planted, real) in cases.items():
            with self.subTest(name):
                self.assertEqual(
                    problems_of(name, set_expect(attempts=planted)),
                    [f"{name}: The responses and client.md give {real} attempts, not {planted}."],
                )

    def test_rejects_too_few_attempts_with_matching_waits(self) -> None:
        edit = set_expect(attempts=2, waitsMs=[{"min": 500, "max": 750}])
        self.assertIn(
            "lookup-retries-exhausted: The responses and client.md give 3 attempts, not 2.",
            problems_of("lookup-retries-exhausted", edit),
        )

    def test_rejects_a_wait_that_client_md_does_not_give(self) -> None:
        cases = {
            "lookup-retry-after": [{"min": 100, "max": 100}],
            "lookup-retry-502": [{"min": 0, "max": 5}],
        }
        for name, waits in cases.items():
            with self.subTest(name):
                [problem] = problems_of(name, set_expect(waitsMs=waits))
                self.assertTrue(problem.startswith(f"{name}: The responses and client.md give"))

    def test_rejects_a_retry_with_no_waits(self) -> None:
        self.assertEqual(
            problems_of("lookup-retry-503", lambda scenario: scenario["expect"].pop("waitsMs")),
            ["lookup-retry-503: A call that retries needs waitsMs."],
        )

    def test_rejects_more_requests_in_flight_than_the_queue_allows(self) -> None:
        self.assertEqual(
            problems_of("lookup-queue-limit", set_expect(maxInFlight=9)),
            ["lookup-queue-limit: client.md gives 4 requests in flight at most, not 9."],
        )


class RequestTest(unittest.TestCase):
    def test_rejects_a_query_value_that_is_not_in_the_shortest_form(self) -> None:
        def write_9_0(scenario: dict[str, Any]) -> None:
            scenario["expect"]["request"]["query"]["lat"] = "9.0"

        [problem] = problems_of("reverse-unit", write_9_0)
        self.assertTrue(problem.startswith('reverse-unit: The first request is {"method": "GET"'))

    def test_writes_each_number_in_its_shortest_decimal_form(self) -> None:
        cases = {9.0: "9", 1e-07: "0.0000001", -0.0: "0", 9.001: "9.001", 250: "250", -7.5: "-7.5"}
        for number, text in cases.items():
            with self.subTest(number=number):
                self.assertEqual(scenario_truth.query_number(number), text)

    def test_the_deadline_of_a_lookup_with_the_defaults_is_26_seconds(self) -> None:
        self.assertEqual(scenario_truth.deadline_ms(8000, 2), 26000)
