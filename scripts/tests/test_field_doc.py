# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for field.md and its message catalogue, and for the files that point to them."""

import json
import re
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FIELD = (ROOT / "field.md").read_text(encoding="utf-8")
CATALOGUE = ROOT / "messages" / "field_en.arb"
STANDARDS = ROOT / "standards" / "CODING_STANDARDS.md"
TYPESCRIPT = ROOT / "standards" / "languages" / "typescript.md"
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def section(heading: str) -> str:
    """Return the text of field.md under a heading, up to the next heading of any level."""
    return re.split(r"\n#+ ", FIELD.partition(f"\n{heading}\n")[2])[0]


def first_cells(heading: str) -> list[str]:
    """Return the first cell of each row of the table under a heading, without backticks."""
    rows = [line for line in section(heading).splitlines() if line.startswith("| ")]
    return [row.split("|")[1].strip().strip("`") for row in rows[1:]]


def catalogue() -> dict[str, Any]:
    document: object = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise TypeError("field_en.arb must hold a JSON object.")
    return document


def messages() -> dict[str, str]:
    return {key: text for key, text in catalogue().items() if not key.startswith("@")}


class CatalogueTest(unittest.TestCase):
    def test_the_catalogue_is_english(self) -> None:
        self.assertEqual(catalogue()["@@locale"], "en")

    def test_field_md_lists_each_key_of_the_catalogue_once(self) -> None:
        keys = first_cells("### Message keys")
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(sorted(keys), sorted(messages()))

    def test_each_message_has_a_description(self) -> None:
        for key in messages():
            with self.subTest(key=key):
                self.assertTrue(catalogue()[f"@{key}"]["description"])

    def test_each_placeholder_in_a_text_is_declared_and_each_declared_one_is_used(self) -> None:
        for key, text in messages().items():
            with self.subTest(key=key):
                declared = catalogue()[f"@{key}"].get("placeholders", {})
                self.assertEqual(set(PLACEHOLDER.findall(text)), set(declared))

    def test_each_state_names_only_keys_of_the_catalogue(self) -> None:
        rows = [line for line in section("## States").splitlines() if line.startswith("| ")]
        cells = [row.split("|")[3] for row in rows[2:]]
        named = {key for cell in cells for key in re.findall(r"`([a-z_]+)`", cell)}
        self.assertLessEqual(named, set(messages()))


class InterfaceTest(unittest.TestCase):
    def test_the_interface_lists_the_settings_events_and_constant(self) -> None:
        self.assertEqual(
            first_cells("## Interface"),
            [
                "name`, `value`, `required`, `disabled",
                "label",
                "apiKey",
                "baseUrl",
                "confirm",
                "gps",
                "legacy",
                "messages",
                "change",
                "confirm",
                "error",
                "SPEC_VERSION",
            ],
        )

    def test_the_change_event_names_each_source(self) -> None:
        change = next(x for x in section("### Events").splitlines() if x.startswith("| `change`"))
        self.assertIn("`typed`, `pasted`, `suggestion` or `gps`", change)

    def test_the_twelve_states_of_the_design_are_listed(self) -> None:
        self.assertEqual(
            first_cells("## States"),
            [
                "idle",
                "typing",
                "invalid format",
                "legacy code",
                "checking",
                "valid",
                "not found",
                "confirmed",
                "error",
                "GPS locating",
                "GPS coarse",
                "GPS denied",
            ],
        )

    def test_a_lookup_never_blocks_the_form(self) -> None:
        self.assertIn("A lookup never changes the validity.", section("## Form value and validity"))

    def test_the_field_never_shows_the_house_address(self) -> None:
        self.assertIn("It never shows `recentHouseAddress`", section("## Lookups"))


class PointerTest(unittest.TestCase):
    def test_the_standards_send_the_reader_to_field_md(self) -> None:
        lines = STANDARDS.read_text(encoding="utf-8").splitlines()
        ranking = next(x for x in lines if "rank above this document" in x)
        api_1 = next(x for x in lines if x.startswith("- **API-1"))
        self.assertIn("`spec/field.md`", ranking)
        self.assertIn("`spec/messages/`", ranking)
        self.assertIn("`spec/field.md`", api_1)

    def test_the_agents_template_names_each_interface_section(self) -> None:
        template = (ROOT / "templates" / "AGENTS.md").read_text(encoding="utf-8")
        rule = next(x for x in template.splitlines() if "public symbol" in x)
        for name in ("`spec/grammar.md`", "`spec/client.md`", "`spec/field.md`"):
            self.assertIn(name, rule)

    def test_the_typescript_file_names_the_additions_of_the_field(self) -> None:
        text = TYPESCRIPT.read_text(encoding="utf-8")
        additions = text.partition("### Idiomatic additions (API-1)")[2].partition("\n## ")[0]
        for name in ("PostcodeFieldElement", "ChangeDetail", "PostcodeFieldProps", "Messages"):
            self.assertIn(f"`{name}`", additions)
        self.assertNotIn("monocart", text)

    def test_the_readme_lists_field_md_and_the_catalogues(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("| `field.md` |", readme)
        self.assertIn("| `messages/` |", readme)
