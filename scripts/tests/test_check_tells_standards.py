# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests that the check-tells section of the standards says what the tool does."""

import unittest
from pathlib import Path

from check_tells import check_squash_message, check_text

from tests.check_tells_driver import rules
from tests.check_tells_samples import E_ACUTE, PLACEHOLDER_PARAGRAPH, squash

STANDARDS = Path(__file__).resolve().parents[2] / "standards" / "CODING_STANDARDS.md"


def bullet(label: str) -> str:
    """Return the bullet of the check-tells section that starts with this bold label."""
    text = STANDARDS.read_text(encoding="utf-8")
    section = text.partition("### The `check-tells` script")[2].partition("\n## ")[0]
    found = [line for line in section.splitlines() if line.startswith(f"- **{label}")]
    if len(found) != 1:
        raise AssertionError(f"The section has {len(found)} bullets for {label!r}.")
    return found[0]


class TemplateTextRuleTest(unittest.TestCase):
    def test_names_each_template_text_check_under_the_rule_that_the_tool_reports(self) -> None:
        checks = {PLACEHOLDER_PARAGRAPH: "placeholder paragraph", "Closes #": "`Closes #`"}
        for body, phrase in checks.items():
            with self.subTest(phrase=phrase):
                [rule] = rules(check_squash_message(squash("fix: a unit", body=body)))
                self.assertIn(phrase, bullet(f"{rule}."))

    def test_names_no_template_text_check_under_the_sign_off_rule(self) -> None:
        sign_off = bullet("GIT-2.")
        self.assertNotIn("placeholder paragraph", sign_off)
        self.assertNotIn("Closes #", sign_off)


class DataFileTest(unittest.TestCase):
    def test_holds_a_json_data_file_to_ascii(self) -> None:
        found = check_text("data/states.json", f'{{"name": "Caf{E_ACUTE}"}}')
        self.assertEqual(rules(found), ["TELL-14"])
        config = bullet("Config files")
        self.assertIn("JSON data file", config)
        self.assertIn("ASCII", config)

    def test_lets_a_data_file_of_another_type_use_any_script(self) -> None:
        self.assertEqual(check_text("data/names.csv", f"Caf{E_ACUTE}"), [])
        self.assertIn("`.csv`", bullet("Other files"))
