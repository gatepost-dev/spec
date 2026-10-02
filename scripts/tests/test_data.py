# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the shared data files, and for the grammar text that repeats their values."""

import json
import re
import unittest
from itertools import accumulate
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SEGMENT_NAMES = ["state", "lga", "district", "area", "unit"]
# The states where NIPOST's code is not the ISO 3166-2:NG code. Name: (code, iso).
NIPOST_CODES_OFF_ISO = {
    "Borno": ("BR", "NG-BO"),
    "Gombe": ("GM", "NG-GO"),
    "Kogi": ("KG", "NG-KO"),
    "Sokoto": ("SK", "NG-SO"),
    "Yobe": ("YB", "NG-YO"),
}


def load(name: str) -> dict[str, Any]:
    document: object = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise TypeError(f"{name} must hold a JSON object.")
    return document


def grammar_text() -> str:
    return (ROOT / "grammar.md").read_text(encoding="utf-8")


def grammar_section(heading: str) -> str:
    """Return the text under a second-level heading of grammar.md, up to the next heading."""
    for section in re.split(r"^## ", grammar_text(), flags=re.MULTILINE):
        if section.startswith(heading + "\n"):
            return section
    raise AssertionError(f"grammar.md has no section {heading!r}.")


def integers_after(anchor: str) -> list[int]:
    """Return the integers in the sentence of grammar.md that follows the anchor text."""
    sentence = re.search(re.escape(anchor) + r"([^.]*)\.", grammar_text())
    if sentence is None:
        raise AssertionError(f"grammar.md has no sentence that follows {anchor!r}.")
    return [int(number) for number in re.findall(r"\d+", sentence.group(1))]


class StatesTest(unittest.TestCase):
    def test_lists_37_states_in_code_order(self) -> None:
        codes = [state["code"] for state in load("states.json")["states"]]
        self.assertEqual(len(codes), 37)
        self.assertEqual(codes, sorted(set(codes)))

    def test_uses_two_capital_letters_for_each_code(self) -> None:
        for state in load("states.json")["states"]:
            with self.subTest(code=state["code"]):
                self.assertRegex(state["code"], r"^[A-Z]{2}$")
                self.assertTrue(state["name"].isascii())
                self.assertNotEqual(state["name"].strip(), "")

    def test_keeps_the_iso_code_of_each_state_beside_the_nipost_code(self) -> None:
        seen: list[str] = []
        for state in load("states.json")["states"]:
            seen.append(state["name"])
            with self.subTest(name=state["name"]):
                self.assertRegex(state["iso"], r"^NG-[A-Z]{2}$")
                if state["name"] in NIPOST_CODES_OFF_ISO:
                    self.assertEqual(
                        (state["code"], state["iso"]), NIPOST_CODES_OFF_ISO[state["name"]]
                    )
                else:
                    self.assertEqual(state["iso"], "NG-" + state["code"])
        self.assertEqual(sorted(set(NIPOST_CODES_OFF_ISO) - set(seen)), [])


class PrecisionTest(unittest.TestCase):
    def test_raises_the_limit_as_precision_falls(self) -> None:
        precision_rules = load("precision.json")
        limits = [row["maxAccuracyM"] for row in precision_rules["thresholds"]]
        self.assertEqual(limits, sorted(limits))
        threshold_precisions = [row["precision"] for row in precision_rules["thresholds"]]
        precision_names = [*threshold_precisions, precision_rules["fallback"]]
        self.assertEqual(precision_names, ["unit", "area", "district", "lga"])


class FormatTest(unittest.TestCase):
    def test_names_five_segments_of_11_characters(self) -> None:
        segments = load("format.json")["segments"]
        self.assertEqual([segment["name"] for segment in segments], SEGMENT_NAMES)
        self.assertEqual(sum(segment["length"] for segment in segments), 11)

    def test_describes_each_segment_with_a_known_word_for_its_characters(self) -> None:
        for segment in load("format.json")["segments"]:
            with self.subTest(segment=segment["name"]):
                self.assertIn(segment["characters"], {"letters", "digits", "letters-or-digits"})
                if "minimum" in segment:
                    self.assertEqual(segment["characters"], "digits")

    def test_writes_each_separator_as_a_code_point(self) -> None:
        for label in load("format.json")["separators"]:
            with self.subTest(label=label):
                self.assertRegex(label, r"^U\+[0-9A-F]{4}$")

    def test_matches_a_legacy_code_of_exactly_six_ascii_digits(self) -> None:
        pattern = load("format.json")["legacyPattern"]
        arabic_indic_digits = "".join(chr(0x0660 + digit) for digit in (9, 0, 0, 1, 0, 8))
        cases = [
            ("900108", True),
            ("90010", False),
            ("9001081", False),
            ("90010A", False),
            ("", False),
            (arabic_indic_digits, False),
        ]
        for text, matches in cases:
            with self.subTest(text=ascii(text)):
                self.assertEqual(re.fullmatch(pattern, text) is not None, matches)

    def test_limits_the_input_to_64_code_points(self) -> None:
        self.assertEqual(load("format.json")["maxInputCodePoints"], 64)


class GrammarTextTest(unittest.TestCase):
    """grammar.md repeats some values of data/format.json, so that a reader needs no other file."""

    def test_the_segment_table_matches_the_segments(self) -> None:
        segments = load("format.json")["segments"]
        state_count = len(load("states.json")["states"])
        lines = grammar_section("Segments").splitlines()
        rows = [
            line for line in lines if line.startswith("| ") and not line.startswith("| Segment")
        ]
        cells = [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]
        self.assertEqual([row[0] for row in cells], [segment["name"] for segment in segments])
        for row, segment in zip(cells, segments, strict=True):
            with self.subTest(segment=segment["name"]):
                length = segment["length"]
                self.assertEqual(int(row[1]), length)
                self.assertEqual(row[2].replace(" or ", "-or-"), segment["characters"])
                if "minimum" in segment:
                    expected = [f"{segment['minimum']:0{length}d}", "9" * length]
                elif segment["name"] == "state":
                    # The rule of the state segment counts the codes in states.json.
                    expected = [str(state_count)]
                else:
                    expected = []
                self.assertEqual(re.findall(r"\d+", row[3]), expected)

    def test_the_partial_lengths_are_the_sums_of_the_segment_lengths(self) -> None:
        lengths = [segment["length"] for segment in load("format.json")["segments"]]
        ends = list(accumulate(lengths))
        self.assertEqual(integers_after("Its length is"), ends[:-1])
        self.assertEqual(integers_after("the length is not"), ends[-1:])
        self.assertEqual(integers_after("the lengths"), ends[:-1])

    def test_the_input_limit_matches_max_input_code_points(self) -> None:
        limit = load("format.json")["maxInputCodePoints"]
        cited = re.findall(r"\((\d+) in `data/format.json`\)", grammar_text())
        self.assertEqual(cited, [str(limit)])
        self.assertEqual(integers_after("An SDK can stop counting at"), [limit + 1])

    def test_the_legacy_rule_matches_the_legacy_pattern(self) -> None:
        pattern = load("format.json")["legacyPattern"]
        counts = [int(count) for count in re.findall(r"exactly (\d+) ASCII digits", grammar_text())]
        # The legacy_code check and the isLegacy section both state the rule.
        self.assertGreaterEqual(len(counts), 2)
        for count in counts:
            with self.subTest(count=count):
                self.assertTrue(re.fullmatch(pattern, "0" * count))
                self.assertFalse(re.fullmatch(pattern, "0" * (count - 1)))
                self.assertFalse(re.fullmatch(pattern, "0" * (count + 1)))

    def test_the_fixes_match_the_suggestions(self) -> None:
        suggestions = load("format.json")["suggestions"]
        lead_ins = {"letters": "- In the letter segments", "digits": "- In the digit segments"}
        # A kind of segment with no table keeps its characters, so the district has no fixes.
        self.assertEqual(sorted(suggestions), sorted(lead_ins))
        lines = grammar_section("Suggestions").splitlines()
        for kind, lead_in in lead_ins.items():
            with self.subTest(kind=kind):
                line = next((line for line in lines if line.startswith(lead_in)), "")
                self.assertEqual(dict(re.findall(r"`(.)` to `(.)`", line)), suggestions[kind])
