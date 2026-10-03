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
CLIENT = (ROOT / "client.md").read_text(encoding="utf-8")
CATALOGUE = ROOT / "messages" / "field_en.arb"
STANDARDS = ROOT / "standards" / "CODING_STANDARDS.md"
TYPESCRIPT = ROOT / "standards" / "languages" / "typescript.md"
PLACEHOLDER = re.compile(r"\{(\w+)\}")
CODE = re.compile(r"`([a-z_]+)`")
FIELD_CODES = {"secret_key", "gps_denied", "gps_unavailable"}
STATES = [
    "GPS locating",
    "checking",
    "confirmed",
    "not found",
    "error",
    "GPS coarse",
    "GPS denied",
    "legacy code",
    "valid",
    "invalid format",
    "typing",
    "idle",
]


def section(heading: str) -> str:
    """Return the text of field.md under a heading, up to the next heading of any level."""
    return re.split(r"\n#+ ", FIELD.partition(f"\n{heading}\n")[2])[0]


def rows(heading: str) -> list[list[str]]:
    """Return the cells of each row of the table under a heading, after its header row."""
    lines = [line for line in section(heading).splitlines() if line.startswith("| ")]
    return [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines[1:]]


def first_cells(heading: str) -> list[str]:
    """Return the first cell of each row of the table under a heading, without backticks."""
    return [cells[0].strip("`") for cells in rows(heading)]


def catalogue() -> dict[str, Any]:
    document: object = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise TypeError("field_en.arb must hold a JSON object.")
    return document


def messages() -> dict[str, str]:
    return {key: text for key, text in catalogue().items() if not key.startswith("@")}


def client_codes() -> set[str]:
    """Return the error codes of the client, from the table of codes in client.md."""
    lines = CLIENT.partition("\n## Errors\n")[2].partition("\n## ")[0].splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| Condition |"))
    codes: set[str] = set()
    for line in lines[start + 2 :]:
        if not line.startswith("| "):
            break
        codes.update(CODE.findall(line.split("|")[2]))
    return codes


def sentences(text: str) -> list[str]:
    """Return the sentences of the prose and the table cells of a Markdown text."""
    found: list[str] = []
    for line in text.splitlines():
        if line.startswith("#") or set(line) <= set("|-"):
            continue
        for part in line.strip("|").split(" | "):
            body = re.sub(r"^\s*- ", "", part).strip()
            found.extend(x for x in re.split(r"(?<=[.?!])\s+", body) if x)
    return found


class CatalogueTest(unittest.TestCase):
    def test_the_catalogue_is_english(self) -> None:
        self.assertEqual(catalogue()["@@locale"], "en")

    def test_field_md_lists_each_key_of_the_catalogue_once(self) -> None:
        keys = first_cells("### Message keys")
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(sorted(keys), sorted(messages()))

    def test_field_md_names_the_placeholders_of_each_message(self) -> None:
        for cells in rows("### Message keys"):
            key = cells[0].strip("`")
            with self.subTest(key=key):
                named = set(re.findall(r"`\{(\w+)\}`", cells[1]))
                self.assertEqual(cells[1] == "none", not named)
                declared = catalogue()[f"@{key}"].get("placeholders", {})
                self.assertEqual(named, set(declared))

    def test_each_message_has_a_description(self) -> None:
        for key in messages():
            with self.subTest(key=key):
                self.assertTrue(catalogue()[f"@{key}"]["description"])

    def test_each_placeholder_in_a_text_is_declared_and_each_declared_one_is_used(self) -> None:
        for key, text in messages().items():
            with self.subTest(key=key):
                declared = catalogue()[f"@{key}"].get("placeholders", {})
                self.assertEqual(set(PLACEHOLDER.findall(text)), set(declared))

    def test_each_line_of_the_catalogue_has_100_characters_or_fewer(self) -> None:
        for number, line in enumerate(CATALOGUE.read_text(encoding="utf-8").splitlines(), 1):
            with self.subTest(line=number):
                self.assertLessEqual(len(line), 100)

    def test_the_coarse_message_fits_every_partial_postcode_from_a_location(self) -> None:
        text = messages()["gps_coarse"]
        self.assertEqual(PLACEHOLDER.findall(text), [])
        for word in ("first", "accurate", "metres"):
            self.assertNotIn(word, text)

    def test_each_state_names_only_keys_of_the_catalogue(self) -> None:
        cells = [row[2] for row in rows("## States")]
        self.assertEqual(len(cells), len(STATES))
        named = {key for cell in cells for key in CODE.findall(cell)}
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

    def test_an_empty_key_counts_as_no_key(self) -> None:
        api_key = next(x for x in rows("## Interface") if x[0] == "`apiKey`")
        self.assertIn("An empty key counts as no key.", api_key[2])

    def test_the_change_event_names_each_source(self) -> None:
        change = next(x for x in section("### Events").splitlines() if x.startswith("| `change`"))
        self.assertIn("`typed`, `pasted`, `suggestion` or `gps`", change)

    def test_the_twelve_states_of_the_design_are_listed_in_their_order(self) -> None:
        self.assertEqual(first_cells("## States"), STATES)
        lead = "The field shows the first state in this table whose condition holds."
        self.assertIn(lead, section("## States"))

    def test_each_failure_gives_a_state_a_message_and_an_event_code(self) -> None:
        client = "the code of the client's error"
        self.assertEqual(
            [(cells[1], cells[2], cells[3].partition(",")[0]) for cells in rows("## Failures")],
            [
                ("not found", "`not_found`", "no event"),
                ("error", "`check_failed`", client),
                ("error", "`secret_key`", "`secret_key`"),
                ("GPS denied", "`gps_denied`", "`gps_denied`"),
                ("GPS denied", "`gps_unavailable`", "`gps_unavailable`"),
                ("GPS denied", "`gps_unavailable`", "`gps_unavailable`"),
                ("GPS denied", "`gps_unavailable`", client),
                ("GPS denied", "`gps_not_found`", "no event"),
            ],
        )

    def test_each_event_code_of_a_failure_is_a_code_of_the_client_or_the_field(self) -> None:
        error = next(x for x in rows("### Events") if x[0] == "`error`")
        self.assertEqual(set(CODE.findall(error[1].partition(": ")[2])), FIELD_CODES)
        for cells in rows("## Failures"):
            with self.subTest(failure=cells[0]):
                self.assertLessEqual(set(CODE.findall(cells[3])), client_codes() | FIELD_CODES)
                self.assertIn(cells[2].strip("`"), messages())

    def test_a_lookup_never_blocks_the_form(self) -> None:
        self.assertIn("A lookup never changes the validity.", section("## Form value and validity"))

    def test_an_invalid_field_reports_its_message(self) -> None:
        part = section("## Form value and validity")
        self.assertIn("An invalid field reports the text of its message", part)
        self.assertIn("The setting `value` gives the first text.", part)


class TextTest(unittest.TestCase):
    def test_a_text_above_the_input_limit_is_never_normalised(self) -> None:
        part = section("## Text")
        self.assertIn("the field never calls `normalize`", part)
        self.assertIn("The count is then the number of code points of the raw text.", part)

    def test_the_parse_error_and_the_suggestion_stay_two_texts(self) -> None:
        self.assertIn("never one joined string (UI-2)", section("## Text"))

    def test_the_display_form_sends_no_new_lookup(self) -> None:
        part = section("## Lookups")
        self.assertIn("the field keeps that lookup and its outcome", part)

    def test_the_console_error_never_holds_the_key(self) -> None:
        self.assertIn("The error never holds the key (ERR-3).", section("## Lookups"))


class LocationTest(unittest.TestCase):
    part = section("## Location")

    def test_a_fallback_is_truncated_to_the_precision_of_the_fix(self) -> None:
        self.assertIn("The field truncates the postcode to that precision", self.part)
        self.assertIn("a fix worse than 50 m keeps the state and the LGA only", self.part)

    def test_the_fill_ends_in_a_space_and_takes_the_focus(self) -> None:
        self.assertIn("A partial postcode ends in a space", self.part)
        self.assertIn("The input takes the focus", self.part)
        self.assertIn("It raises `change` with the source `gps`", self.part)

    def test_a_platform_with_no_location_api_gives_gps_unavailable(self) -> None:
        self.assertIn(
            "A platform with no location API gives the failure `gps_unavailable`", self.part
        )


class PrivacyTest(unittest.TestCase):
    def test_the_field_never_shows_a_house_address(self) -> None:
        self.assertIn(
            "The field never shows a house address, neither the `recentHouseAddress` of a lookup"
            " nor the `address` of a reverse unit.",
            section("## Privacy"),
        )


class ProseTest(unittest.TestCase):
    def test_each_sentence_of_field_md_has_25_words_or_fewer(self) -> None:
        for sentence in sentences(FIELD):
            with self.subTest(sentence=sentence):
                self.assertLessEqual(len(sentence.split()), 25)

    def test_field_md_and_the_catalogue_use_no_phrasal_verb_that_a_review_found(self) -> None:
        text = FIELD + CATALOGUE.read_text(encoding="utf-8")
        for verb in ("looks up", "look up", "fills in", "fill in", "filled in"):
            self.assertNotIn(verb, text)


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
        names = (
            "PostcodeFieldElement",
            "ChangeDetail",
            "PostcodeFieldProps",
            "Messages",
            "formAssociated",
            "observedAttributes",
            "connectedCallback()",
            "disconnectedCallback()",
            "attributeChangedCallback()",
            "formResetCallback()",
            "formDisabledCallback()",
            "formStateRestoreCallback()",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", additions)
        self.assertNotIn("monocart", text)

    def test_the_glossary_and_field_md_give_one_form_value(self) -> None:
        context = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        entry = context.partition("**Form value**:\n")[2].partition("\n")[0]
        self.assertIn("without white space at the start and the end", entry)
        self.assertIn("without white space at the start and the end", FIELD)

    def test_the_readme_lists_field_md_and_the_catalogues(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("| `field.md` |", readme)
        self.assertIn("| `messages/` |", readme)
