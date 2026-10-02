# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for build_vectors."""

import json
import math
import string
import unicodedata
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

import build_vectors

ROOT = Path(__file__).resolve().parents[2]
ZERO_WIDTH_JOINER = chr(0x200D)
ASCII_UPPER_CASE = str.maketrans(string.ascii_lowercase, string.ascii_uppercase)


def load(stem: str) -> dict[str, Any]:
    value: object = json.loads((ROOT / "vectors" / f"{stem}.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{stem}.json must hold a JSON object.")
    return value


def utf16_units(text: str) -> int:
    return len(text.encode("utf-16-le", errors="surrogatepass")) // 2


def separator_characters() -> frozenset[str]:
    return frozenset(chr(code_point) for code_point in build_vectors.load_separators())


def holds_only_ascii_and_separators(text: str, separators: frozenset[str]) -> bool:
    return all(character.isascii() or character in separators for character in text)


def table_form(character: str, separators: frozenset[str]) -> str:
    """Return the NFKC form of a character if the form holds only ASCII characters and separators.

    An SDK that applies NFKC through a table has entries for such characters only. It keeps
    every other character as it is.
    """
    form = unicodedata.normalize("NFKC", character)
    if holds_only_ascii_and_separators(form, separators):
        return form
    return character


def remove_separators_and_upper_case(text: str, separators: frozenset[str]) -> str:
    """Apply steps 2 and 3 of the Normalise section in grammar.md."""
    kept = "".join(character for character in text if character not in separators)
    return kept.translate(ASCII_UPPER_CASE)


def full_normalize(text: str, separators: frozenset[str]) -> str:
    """Normalise as grammar.md says, with a full NFKC."""
    return remove_separators_and_upper_case(unicodedata.normalize("NFKC", text), separators)


def reduced_normalize(text: str, separators: frozenset[str]) -> str:
    """Normalise as an SDK without a full NFKC does (grammar.md, section Normalise)."""
    mapped = "".join(table_form(character, separators) for character in text)
    return remove_separators_and_upper_case(mapped, separators)


class BuildVectorsTest(unittest.TestCase):
    def assert_same_text(self, actual: str, expected: str) -> None:
        # ASCII forms keep a failure readable: U+00B5 and U+03BC look alike.
        self.assertEqual(ascii(actual), ascii(expected))

    def test_vector_files_match_the_builder(self) -> None:
        self.assertEqual(build_vectors.main(["--check"]), 0)

    def test_vector_files_are_ascii(self) -> None:
        for path in sorted((ROOT / "vectors").glob("*.json")):
            with self.subTest(file=path.name):
                self.assertTrue(path.read_text(encoding="utf-8").isascii())

    def test_each_case_has_a_unique_id_and_a_description(self) -> None:
        ids: list[str] = []
        for stem in build_vectors.FILES:
            for case in load(stem)["cases"]:
                ids.append(case["id"])
                self.assertTrue(case["description"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 200)

    def test_each_description_is_unique_across_all_vector_files(self) -> None:
        counts = Counter(
            case["description"] for stem in build_vectors.FILES for case in load(stem)["cases"]
        )
        repeated = sorted(text for text, count in counts.items() if count > 1)
        self.assertEqual(repeated, [])

    def test_each_state_has_a_parse_case_and_a_name_case(self) -> None:
        states = json.loads((ROOT / "data" / "states.json").read_text(encoding="utf-8"))
        codes = {state["code"] for state in states["states"]}
        parsed = {case["input"][:2] for case in load("parse-states")["cases"]}
        named = {case["input"] for case in load("state-name")["cases"]}
        self.assertEqual(parsed, codes)
        self.assertLessEqual(codes, named)

    def test_each_unused_iso_code_has_a_state_name_case_and_a_parse_case(self) -> None:
        states = json.loads((ROOT / "data" / "states.json").read_text(encoding="utf-8"))["states"]
        iso_codes = [
            state["iso"].removeprefix("NG-")
            for state in states
            if state["iso"] != "NG-" + state["code"]
        ]
        self.assertTrue(iso_codes)
        unknown_state = {
            "ok": False,
            "error": {"code": "unknown_state", "segment": "state", "suggestion": None},
        }
        nameless = {
            case["input"] for case in load("state-name")["cases"] if case["expect"]["value"] is None
        }
        rejected = {
            case["input"][:2]
            for case in load("parse-segments")["cases"]
            if case["expect"] == unknown_state and not case["options"]
        }
        missing: list[str] = []
        for iso_code in iso_codes:
            if iso_code not in nameless:
                missing.append(f"state-name: {iso_code}")
            if iso_code not in rejected:
                missing.append(f"parse-segments: {iso_code}")
        self.assertEqual(missing, [])

    def test_each_separator_has_a_normalize_case(self) -> None:
        postcode_format = json.loads((ROOT / "data" / "format.json").read_text(encoding="utf-8"))
        expected = {"value": "EK01A03FK01"}
        inputs = {
            case["input"] for case in load("normalize")["cases"] if case["expect"] == expected
        }
        missing: list[str] = []
        for label in postcode_format["separators"]:
            separator = chr(int(label.removeprefix("U+"), 16))
            if separator.join(("EK", "01", "A03", "FK", "01")) not in inputs:
                missing.append(label)
        self.assertEqual(missing, [])

    def test_each_separator_has_an_nfkc_form_of_ascii_characters_and_separators(self) -> None:
        separators = separator_characters()
        # Otherwise full NFKC leaves a character where a table removes the separator.
        outside = [
            f"U+{ord(separator):04X}"
            for separator in sorted(separators)
            if not holds_only_ascii_and_separators(
                unicodedata.normalize("NFKC", separator), separators
            )
        ]
        self.assertEqual(outside, [])

    def test_each_normalize_case_holds_with_full_nfkc_and_with_a_table(self) -> None:
        separators = separator_characters()
        normalizers = {"full NFKC": full_normalize, "NFKC through a table": reduced_normalize}
        for case in load("normalize")["cases"]:
            for name, normalizer in normalizers.items():
                with self.subTest(case["id"], normalizer=name):
                    self.assert_same_text(
                        normalizer(case["input"], separators), case["expect"]["value"]
                    )

    def test_a_table_keeps_a_micro_sign_but_changes_a_full_width_letter(self) -> None:
        separators = separator_characters()
        micro_sign = chr(0x00B5)
        full_width_a = chr(0xFF21)
        with self.subTest("full NFKC changes the micro sign"):
            self.assert_same_text(full_normalize(micro_sign, separators), chr(0x03BC))
        with self.subTest("a table keeps the micro sign"):
            self.assert_same_text(reduced_normalize(micro_sign, separators), micro_sign)
        with self.subTest("a table changes the full-width letter"):
            self.assert_same_text(reduced_normalize(full_width_a, separators), "A")

    def test_each_gps_limit_has_a_case_at_the_limit_and_a_case_above_it(self) -> None:
        rules = json.loads((ROOT / "data" / "precision.json").read_text(encoding="utf-8"))
        limits = [threshold["maxAccuracyM"] for threshold in rules["thresholds"]]
        at_limit = [threshold["precision"] for threshold in rules["thresholds"]]
        above_limit = [*at_limit[1:], rules["fallback"]]
        ceilings = [*limits[1:], math.inf]
        measured = [
            (case["input"], case["expect"]["value"])
            for case in load("precision-for-accuracy")["cases"]
            if isinstance(case["input"], int | float)
        ]
        for limit, ceiling, precision, next_precision in zip(
            limits, ceilings, at_limit, above_limit, strict=True
        ):
            with self.subTest(limit=limit):
                self.assertIn((limit, precision), measured)
                above = [expected for metres, expected in measured if limit < metres < ceiling]
                self.assertIn(next_precision, above)

    def test_parse_has_cases_at_the_limit_above_it_and_for_each_counting_mistake(self) -> None:
        postcode_format = json.loads((ROOT / "data" / "format.json").read_text(encoding="utf-8"))
        limit = postcode_format["maxInputCodePoints"]
        parsed = [
            (case["input"], "ok" if case["expect"]["ok"] else case["expect"]["error"]["code"])
            for case in load("parse")["cases"]
        ]
        outcomes = [(len(text), outcome) for text, outcome in parsed]
        self.assertIn((limit, "ok"), outcomes)
        self.assertIn((limit + 1, "bad_length"), outcomes)
        accepted = [text for text, outcome in parsed if outcome == "ok" and len(text) <= limit]
        rejected = [
            text for text, outcome in parsed if outcome == "bad_length" and len(text) > limit
        ]
        pins = {
            "a success with more UTF-16 units than the limit": [
                text for text in accepted if utf16_units(text) > limit
            ],
            "a success with the limit in code points and more UTF-16 units": [
                text for text in accepted if len(text) == limit and utf16_units(text) > limit
            ],
            "a success that grows past the limit under NFKC": [
                text for text in accepted if len(unicodedata.normalize("NFKC", text)) > limit
            ],
            "a rejection over the limit with a combining mark": [
                text
                for text in rejected
                if any(unicodedata.combining(character) for character in text)
            ],
            "a rejection over the limit that ends in a line feed": [
                text for text in rejected if text.endswith("\n")
            ],
        }
        for requirement, texts in pins.items():
            with self.subTest(requirement):
                self.assertTrue(texts)
        # A check that ends in $ instead of \z skips a final line feed. Only an input with
        # exactly one code point over the limit shows it.
        line_feed_lengths = {len(text) for text in rejected if text.endswith("\n")}
        with self.subTest("each rejection that ends in a line feed is one code point over"):
            self.assertEqual(line_feed_lengths, {limit + 1})

    def test_is_legacy_has_cases_at_the_limit_above_it_and_for_each_counting_mistake(self) -> None:
        postcode_format = json.loads((ROOT / "data" / "format.json").read_text(encoding="utf-8"))
        limit = postcode_format["maxInputCodePoints"]
        legacy = [(case["input"], case["expect"]["value"]) for case in load("is-legacy")["cases"]]
        outcomes = [(len(text), outcome) for text, outcome in legacy]
        self.assertIn((limit, True), outcomes)
        self.assertIn((limit + 1, False), outcomes)
        accepted = [text for text, outcome in legacy if outcome is True and len(text) <= limit]
        rejected = [text for text, outcome in legacy if outcome is False and len(text) > limit]
        pins = {
            "an accepted legacy code that grows past the limit under NFKC": [
                text for text in accepted if len(unicodedata.normalize("NFKC", text)) > limit
            ],
            "a rejected legacy code that is within the limit without its zero-width joiners": [
                text for text in rejected if len(text.replace(ZERO_WIDTH_JOINER, "")) <= limit
            ],
            "a rejected legacy code over the limit that ends in a line feed": [
                text for text in rejected if text.endswith("\n")
            ],
        }
        for requirement, texts in pins.items():
            with self.subTest(requirement):
                self.assertTrue(texts)
        # The same one-over rule as for parse: a check that ends in $ lets such an input through.
        line_feed_lengths = {len(text) for text in rejected if text.endswith("\n")}
        with self.subTest("each rejection that ends in a line feed is one code point over"):
            self.assertEqual(line_feed_lengths, {limit + 1})
