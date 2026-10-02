# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the shared data files."""

import json
import re
import unittest
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
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


class StatesTest(unittest.TestCase):
    def test_lists_37_states_in_code_order(self) -> None:
        codes = [state["code"] for state in load("states.json")["states"]]
        self.assertEqual(len(codes), 37)
        self.assertEqual(codes, sorted(set(codes)))

    def test_uses_two_capital_letters_for_each_code(self) -> None:
        for state in load("states.json")["states"]:
            with self.subTest(code=state["code"]):
                self.assertRegex(state["code"], r"^[A-Z]{2}$")
                self.assertTrue(state["name"].isascii() and state["name"].strip())

    def test_keeps_the_iso_code_of_each_state_beside_the_nipost_code(self) -> None:
        for state in load("states.json")["states"]:
            with self.subTest(name=state["name"]):
                self.assertRegex(state["iso"], r"^NG-[A-Z]{2}$")
                if state["name"] in NIPOST_CODES_OFF_ISO:
                    self.assertEqual(
                        (state["code"], state["iso"]), NIPOST_CODES_OFF_ISO[state["name"]]
                    )
                else:
                    self.assertEqual(state["iso"], "NG-" + state["code"])


class PrecisionTest(unittest.TestCase):
    def test_raises_the_limit_as_precision_falls(self) -> None:
        precision_rules = load("precision.json")
        limits = [row["maxAccuracyM"] for row in precision_rules["thresholds"]]
        self.assertEqual(limits, sorted(limits))
        threshold_precisions = [row["precision"] for row in precision_rules["thresholds"]]
        names = [*threshold_precisions, precision_rules["fallback"]]
        self.assertEqual(names, ["unit", "area", "district", "lga"])


class FormatTest(unittest.TestCase):
    def test_names_five_segments_of_11_characters(self) -> None:
        segments = load("format.json")["segments"]
        self.assertEqual([segment["name"] for segment in segments], SEGMENT_NAMES)
        self.assertEqual(sum(segment["length"] for segment in segments), 11)

    def test_writes_each_separator_as_a_code_point(self) -> None:
        for label in load("format.json")["separators"]:
            with self.subTest(label=label):
                self.assertRegex(label, r"^U\+[0-9A-F]{4}$")

    def test_compiles_the_legacy_pattern(self) -> None:
        self.assertTrue(re.fullmatch(load("format.json")["legacyPattern"], "900108"))

    def test_limits_the_input_to_64_code_points(self) -> None:
        self.assertEqual(load("format.json")["maxInputCodePoints"], 64)
