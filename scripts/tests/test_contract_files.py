# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for contract_files: client.md lists the error codes, and the standards point to it."""

import tempfile
import unittest
from pathlib import Path

import contract_files

CODES = contract_files.error_codes()
STANDARDS = contract_files.ROOT / "standards" / "CODING_STANDARDS.md"


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
