# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the shared data files."""

import json
import re
import unittest
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data"
PRECISIONS = ["state", "lga", "district", "area", "unit"]


def load(name: str) -> dict[str, Any]:
    value: object = json.loads((DATA / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{name} must hold a JSON object.")
    return value


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


class PrecisionTest(unittest.TestCase):
    def test_raises_the_limit_as_precision_falls(self) -> None:
        data = load("precision.json")
        limits = [row["maxAccuracyM"] for row in data["thresholds"]]
        self.assertEqual(limits, sorted(limits))
        names = [row["precision"] for row in data["thresholds"]] + [data["fallback"]]
        self.assertEqual(names, ["unit", "area", "district", "lga"])


class FormatTest(unittest.TestCase):
    def test_names_five_segments_of_11_characters(self) -> None:
        segments = load("format.json")["segments"]
        self.assertEqual([segment["name"] for segment in segments], PRECISIONS)
        self.assertEqual(sum(segment["length"] for segment in segments), 11)

    def test_writes_each_separator_as_a_code_point(self) -> None:
        for label in load("format.json")["separators"]:
            with self.subTest(label=label):
                self.assertRegex(label, r"^U\+[0-9A-F]{4}$")

    def test_compiles_the_legacy_pattern(self) -> None:
        self.assertTrue(re.fullmatch(load("format.json")["legacyPattern"], "900108"))
