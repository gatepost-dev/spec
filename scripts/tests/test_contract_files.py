# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for contract_files: client.md lists the error codes, and the standards point to it."""

import tempfile
import unittest
from pathlib import Path

import contract_files

CODES = contract_files.error_codes()
STANDARDS = contract_files.ROOT / "standards" / "CODING_STANDARDS.md"
CLIENT = contract_files.CLIENT_DOC.read_text(encoding="utf-8")


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
        text = STANDARDS.read_text(encoding="utf-8")
        err_1 = next(line for line in text.splitlines() if "**ERR-1" in line)
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


class ClientInputAndUnknownValuesTest(unittest.TestCase):
    def test_keeps_an_unknown_lookup_status_as_text(self) -> None:
        self.assertNotIn("no `status`, or a value that this table does not list", CLIENT)
        self.assertIn("any other value of `status` as it is", CLIENT)

    def test_rejects_a_bad_level_coordinate_or_distance_before_a_request(self) -> None:
        for rule in (
            "A `level` that is not a whole number from 1 to 5",
            "A `lat` that is not finite or is outside -90 to 90",
            "A `lng` that is not finite or is outside -180 to 180",
            "A `maxDistanceM` below 0 or above 250",
        ):
            self.assertIn(rule, CLIENT)

    def test_writes_a_number_in_the_query_as_a_plain_decimal(self) -> None:
        self.assertIn("plain decimal, with no exponent", CLIENT)

    def test_ignores_unknown_fields_and_names_the_scenario(self) -> None:
        self.assertIn("A client ignores a field that the tables above do not list", CLIENT)
        self.assertIn("`unknown-fields`", CLIENT)

    def test_leaves_the_core_only_rule_out_of_the_mock_server_exceptions(self) -> None:
        path = contract_files.ROOT / "standards" / "languages" / "typescript.md"
        section = path.read_text(encoding="utf-8").partition("## The mock server")[2]
        self.assertNotIn("CS-2", section.partition("## Publishing")[0])
